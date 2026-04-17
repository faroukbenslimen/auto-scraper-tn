"""
scripts/ci_smoke.py — tiny smoke test used by CI

This script performs a lightweight import check without hitting the network.
It will exit non-zero if critical imports fail.
"""
import sys

try:
    import scraper
    import requests
    sess = scraper._get_session()
    ok = hasattr(sess, 'get')
    if ok:
        print("SMOKE_OK")
        sys.exit(0)
    else:
        print("SMOKE_FAIL: session missing get")
        sys.exit(2)
except Exception as e:
    print("SMOKE_FAIL:", e)
    sys.exit(1)
