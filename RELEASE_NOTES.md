# Release v1.0

**Release date:** 2026-04-09

## Overview

- Rewrote `scraper.py` to use Selenium + `webdriver-manager` so JS-rendered listings on automobile.tn are correctly extracted.
- The scraper returns a pandas `DataFrame` with columns: `title`, `price_raw`, `year_raw`, `km_raw`, `fuel`, `location`, `link`, `scraped_at`.
- Added dependencies: `selenium`, `webdriver-manager` (see `requirements.txt`).
- Added `.streamlit/config.toml` to avoid Streamlit auto-opening a browser tab.
- Fixed an import collision (renamed `inspect.py`), removed debug utilities (`debug.py`), added `LICENSE` (MIT), and created annotated tag `v1.0`.

## Quick usage

Install requirements:

```
python -m pip install -r requirements.txt
```

Quick test (1 page):

```
python -c "from scraper import scrape_cars; df = scrape_cars(1); print(df.head())"
```

Save results to CSV (3 pages):

```
python - <<PY
from scraper import scrape_cars
df = scrape_cars(3)
df.to_csv('data/cars.csv', index=False)
PY
```

## Notes

- The scraper prefers Chrome via Selenium Manager; if Chrome is not available it will try Edge or fall back to `webdriver-manager`-provided drivers. Ensure a browser binary is present in the environment when running the scraper.
- The Git tag `v1.0` already exists. To create a GitHub Release from this tag locally using the GitHub CLI:

```
gh release create v1.0 --title "v1.0" --notes-file RELEASE_NOTES.md
```

This requires the `gh` CLI and authentication with GitHub.

## Contributors

- Maintainer: faroukbenslimen
