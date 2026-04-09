#!/usr/bin/env python3
"""
Helper: run a headless 3-page scrape and save results to data/cars.csv
"""
import sys
import os
import logging

# ensure repo root is on sys.path so `from scraper import scrape_cars` works
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scraper import scrape_cars


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logging.info("Starting 3-page headless scrape")
    df = scrape_cars(3)
    logging.info("Scraped %d rows", len(df))
    os.makedirs("data", exist_ok=True)
    out = os.path.join("data", "cars.csv")
    df.to_csv(out, index=False)
    logging.info("Saved %s", out)


if __name__ == "__main__":
    main()
