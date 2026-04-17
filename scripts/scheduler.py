"""
scripts/scheduler.py — Simple APScheduler runner for periodic scrapes

Run:
    python scripts/scheduler.py

This uses APScheduler's BlockingScheduler to run `scrape_cars()` on an interval
and persists results with `save_data()`. Configure interval/pages via env:
  - SCRAPER_INTERVAL_MINUTES (default 360)
  - SCRAPE_PAGES (default 2)
"""
import os
import time
import logging
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from scraper import scrape_cars, save_data

try:
    from pythonjsonlogger import jsonlogger
    _has_jsonlogger = True
except Exception:
    _has_jsonlogger = False


logger = logging.getLogger("auto_scraper.scheduler")
handler = logging.StreamHandler()
if _has_jsonlogger:
    fmt = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    handler.setFormatter(fmt)
else:
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _run_job():
    pages = int(os.getenv("SCRAPE_PAGES", "2"))
    logger.info("Starting scheduled scrape", extra={"pages": pages})
    t0 = time.time()
    try:
        df = scrape_cars(num_pages=pages)
        if df is not None and not df.empty:
            save_data(df)
        dur = time.time() - t0
        logger.info("Scheduled scrape finished", extra={"duration_sec": dur, "scraped_rows": 0 if df is None else len(df)})
    except Exception as e:
        logger.exception("Scheduled scrape failed: %s", e)


def main():
    interval_min = int(os.getenv("SCRAPER_INTERVAL_MINUTES", "360"))
    scheduler = BlockingScheduler()
    # Run once immediately, then every `interval_min` minutes
    scheduler.add_job(_run_job, "interval", minutes=interval_min, next_run_time=datetime.now())
    logger.info("Scheduler started", extra={"interval_min": interval_min})
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")


if __name__ == "__main__":
    main()
