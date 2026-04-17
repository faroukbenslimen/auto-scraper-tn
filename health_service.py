"""
health_service.py — lightweight FastAPI health & metrics endpoint

Run:
    python health_service.py

Exposes:
  - GET /healthz    -> basic health and last_sync info
  - GET /metrics    -> JSON metrics: total_listings, last_sync

This service reads `data/metadata.json` and `data/cars.db` for metrics.
"""
import os
import json
import sqlite3
import logging

try:
    from fastapi import FastAPI
    _has_fastapi = True
except Exception:
    FastAPI = None  # type: ignore
    _has_fastapi = False

try:
    from pythonjsonlogger import jsonlogger
    _has_jsonlogger = True
except Exception:
    _has_jsonlogger = False

app = FastAPI() if _has_fastapi else None

logger = logging.getLogger("auto_scraper.health")
handler = logging.StreamHandler()
if _has_jsonlogger:
    handler.setFormatter(jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
else:
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _read_metadata(meta_path: str = "data/metadata.json"):
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _count_listings(db_path: str = "data/cars.db") -> int:
    if not os.path.exists(db_path):
        return 0
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT COUNT(*) FROM cars")
        cnt = cur.fetchone()[0]
        conn.close()
        return int(cnt)
    except Exception:
        return 0


@app.get("/healthz")
def healthz():
    meta = _read_metadata()
    total = _count_listings()
    payload = {
        "status": "ok",
        "total_listings": total,
        "last_sync": meta.get("last_sync"),
        "is_syncing": meta.get("is_syncing", False),
    }
    logger.info("healthz queried", extra={"payload": payload})
    return payload


@app.get("/metrics")
def metrics():
    meta = _read_metadata()
    total = _count_listings()
    payload = {
        "total_listings": total,
        "last_sync": meta.get("last_sync"),
    }
    return payload


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("HEALTH_PORT", "8765"))
    logger.info(f"Starting health service on 0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
