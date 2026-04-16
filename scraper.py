"""
scraper.py — Module de collecte des données automobiles (Selenium)
Site cible : automobile.tn/occasion
"""

import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import pandas as pd
import requests
import concurrent.futures
from bs4 import BeautifulSoup
import random
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import asyncio
import httpx
from lxml import html as lxml_html

# ─── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://www.automobile.tn"
SEARCH_URL = "https://www.automobile.tn/occasion"

DATA_PATH = "data/cars.csv"
EXPECTED_COLUMNS = [
    "title",
    "price_raw",
    "year_raw",
    "km_raw",
    "fuel",
    "location",
    "link",
    "image_url",
    "scraped_at",
]


# ─── HTTP Session (reused across requests) ─────────────────────────────────────
def _get_session():
    """Returns a module-level requests.Session configured for high-concurrency scraping.

    The session is configured with a custom User-Agent, a connection pool sized
    for parallel workers (15), and a robust retry strategy for handling transient
    network errors (429, 500, 502, 503, 504).

    Returns:
        A shared requests.Session instance.
    """
_session = None

def _get_session():
    """Returns a module-level requests.Session configured for high-concurrency scraping.

    The session is configured with a custom User-Agent, a connection pool sized
    for parallel workers (15), and a robust retry strategy for handling transient
    network errors (429, 500, 502, 503, 504).

    Returns:
        A shared requests.Session instance.
    """
    global _session
    if _session is not None:
        return _session

    session = requests.Session()

    # Robust retry strategy for transient network/server errors
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["HEAD", "GET", "OPTIONS"]),
    )

    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=15, pool_maxsize=30)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # Default headers to emulate a modern browser
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })

    _session = session
    return _session


def reset_session():
    """Reset and close the module-level session (useful after errors)."""
    global _session
    try:
        if _session is not None:
            _session.close()
    except Exception:
        pass
    _session = None

# ─── Extraction d'une annonce ──────────────────────────────────────────────────

def _extract_first_text(tag, selectors):
    for selector in selectors:
        found = tag.select_one(selector)
        if found:
            text = found.get_text(" ", strip=True)
            if text:
                return text
    return ""


def _normalize_link(href: str) -> str:
    if not href:
        return "N/A"
    if href.startswith("http"):
        return href
    return urljoin(BASE_URL, href)


def _looks_like_listing_link(href: str) -> bool:
    if not href:
        return False
    h = href.lower().strip()
    if "/occasion/" not in h:
        return False

    # Exclure les pages de navigation et sections non-annonces.
    excluded = [
        "/occasion/recherche",
        "/occasion/du-jour",
        "/occasion/vendeurs-pro",
        "/occasion/comparateur",
    ]
    if any(x in h for x in excluded):
        return False

    if h.rstrip("/") in ("/occasion", "occasion", "/fr/occasion"):
        return False

    # Les vraies annonces contiennent généralement un id numérique dans l'URL.
    if re.search(r"/occasion/.+/\d+", h):
        return True

    # Fallback permissif si la structure change mais reste dans les annonces.
    if "/occasion/" in h and len([p for p in h.split("/") if p]) >= 4:
        return True

    if h.endswith(".jpg") or h.endswith(".png"):
        return False

    return False


def extract_car(card):
    """Parses a single vehicle listing from an HTML container.

    Extracts core attributes including title, price, year, mileage, fuel type,
    location, direct link, and image URL. Uses multiple fallback CSS selectors
    and regex patterns to handle different site layouts.

    Args:
        card: A BeautifulSoup Tag representing the vehicle listing.

    Returns:
        A dictionary containing the car's data, or None if extraction fails.
    """
    try:
        text_blob = card.get_text(" ", strip=True)

        title = _extract_first_text(
            card,
            [
                ".item-title",
                ".title",
                "h1",
                "h2",
                "h3",
                "h4",
                ".name",
                ".car-name",
                "a[title]",
            ],
        )
        if not title:
            main_link = card.find("a", href=True)
            title = main_link.get_text(" ", strip=True) if main_link else "N/A"
        title = title or "N/A"

        price_raw = _extract_first_text(card, [".price", ".prix", ".price-block", "[class*='price']"])
        if not price_raw:
            m_price = re.search(r"\d[\d\s.,]*\s?(?:DT|TND|dinars?)", text_blob, re.I)
            price_raw = m_price.group(0).strip() if m_price else "N/A"

        year_raw = _extract_first_text(card, [".year", "[class*='year']", "[class*='annee']", ".item-infos"])
        if not year_raw:
            m_year = re.search(r"\b(19[89]\d|20[0-3]\d)\b", text_blob)
            year_raw = m_year.group(1) if m_year else "N/A"
        else:
            m_year = re.search(r"\b(19[89]\d|20[0-3]\d)\b", year_raw)
            year_raw = m_year.group(1) if m_year else "N/A"

        km_raw = _extract_first_text(card, [".km", "[class*='mileage']", "[class*='kilom']", ".item-infos"])
        if not km_raw:
            m_km = re.search(r"\d[\d\s.,]*\s?km\b", text_blob, re.I)
            km_raw = m_km.group(0).strip() if m_km else "N/A"
        else:
            m_km = re.search(r"\d[\d\s.,]*\s?km\b", km_raw, re.I)
            km_raw = m_km.group(0).strip() if m_km else "N/A"

        fuel = _extract_first_text(card, [".fuel", "[class*='fuel']", "[class*='carburant']", ".item-infos"])
        if not fuel:
            m_fuel = re.search(r"diesel|essence|hybride|electrique|électrique|gpl", text_blob, re.I)
            fuel = m_fuel.group(0).strip() if m_fuel else "N/A"
        else:
            m_fuel = re.search(r"diesel|essence|hybride|electrique|électrique|gpl", fuel, re.I)
            fuel = m_fuel.group(0).strip() if m_fuel else "N/A"

        location = _extract_first_text(card, [".thumb-infos", ".location", ".city", "[class*='region']", "[class*='ville']"])
        if not location:
            location = "N/A"

        # Normalise les locations trop bavardes en gardant le dernier segment utile.
        if location != "N/A":
            location = re.sub(r"\s+", " ", location).strip()
            if "|" in location:
                location = location.split("|")[-1].strip()

        link = "N/A"
        for a in card.find_all("a", href=True):
            href = a.get("href", "")
            if _looks_like_listing_link(href):
                link = _normalize_link(href)
                break
                
        image_url = "N/A"
        img_tag = card.find("img")
        if img_tag:
            image_url = img_tag.get("src") or img_tag.get("data-src", "N/A")
            if image_url != "N/A" and not image_url.startswith("http"):
                image_url = urljoin(BASE_URL, image_url)

        return {
            "title": title,
            "price_raw": price_raw,
            "year_raw": year_raw,
            "km_raw": km_raw,
            "fuel": fuel,
            "location": location,
            "link": link,
            "image_url": image_url,
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        print(f"  ⚠️  Error extracting a listing : {e}")
        return None


def _extract_cards_from_html(html: str):
    """Extracts all car listing containers from a raw HTML string.

    Uses a two-step approach:
    1. Fast Path: Uses lxml and CSS selectors for high-speed node extraction.
    2. Fallback: Uses BeautifulSoup heuristics to find listings when CSS fails.

    Args:
        html: The raw HTML content of the page.

    Returns:
        A list of BeautifulSoup Tags, each representing a listing.
    """
    # Fast path using lxml cssselect for common card selectors
    try:
        tree = lxml_html.fromstring(html)
        nodes = tree.cssselect("div.occasion-item-v2, div.occasion-item")
        if nodes:
            cards = []
            for n in nodes:
                try:
                    outer = lxml_html.tostring(n, encoding="unicode")
                    soup = BeautifulSoup(outer, "lxml")
                    tag = soup.find()
                    if tag:
                        cards.append(tag)
                except Exception:
                    continue
            if cards:
                return cards
    except Exception:
        # lxml fast path failed — fall back to BeautifulSoup below
        pass

    # Fallback: original BeautifulSoup-based heuristics
    soup = BeautifulSoup(html, "lxml")

    cards = []
    seen_links = set()

    # Sélecteurs observés sur automobile.tn (prioritaires).
    specific_cards = soup.select("div.occasion-item-v2, div.occasion-item")
    if specific_cards:
        return specific_cards

    listing_anchors = [
        a
        for a in soup.find_all("a", href=True)
        if _looks_like_listing_link(a.get("href", ""))
    ]

    for anchor in listing_anchors:
        href = _normalize_link(anchor.get("href", ""))
        if href in seen_links:
            continue

        parent = anchor
        for candidate in anchor.parents:
            if candidate.name not in {"article", "li", "div", "section"}:
                continue
            txt = candidate.get_text(" ", strip=True)
            if len(txt) < 40:
                continue
            if re.search(r"\b(19[89]\d|20[0-3]\d)\b", txt) or re.search(r"\bkm\b", txt, re.I):
                parent = candidate
                break

        cards.append(parent)
        seen_links.add(href)

    return cards


# ─── Scraping paginé ──────────────────────────────────────────────────────────

def scrape_single_page(page: int):
    """Scrapes and parses a single search results page synchronously.

    This function acts as a robust fallback for the async fetcher. It includes
    manual exponential backoff retries and content verification.

    Args:
        page: The page number to scrape.

    Returns:
        A tuple of (page, list_of_car_dicts).
    """
    url = f"{SEARCH_URL}?page={page}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Use module-wide session (configured with retries and backoff)
    session = _get_session()

    page_cars = []
    try:
        # Manual retry loop with exponential backoff + jitter for network robustness
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                resp = session.get(url, timeout=(6, 30), headers=headers)
                status = resp.status_code
                if status != 200:
                    logging.debug(f"page {page} returned status {status}")
                    raise Exception(f"Status {status}")

                html = resp.text
                # If HTML too short, treat as no-content and retry once
                if not html or len(html) < 500:
                    logging.debug(f"page {page} returned short HTML (len={len(html)})")
                    raise Exception("Short HTML")

                cards = _extract_cards_from_html(html)
                if cards:
                    for item in cards:
                        car = extract_car(item)
                        if car:
                            page_cars.append(car)
                break
            except Exception as ie:
                wait = (2 ** (attempt - 1)) + random.uniform(0, 1.0)
                logging.info(f"  ⚠️  Fetch error page {page} attempt {attempt}/{max_attempts}: {ie}; retrying in {wait:.1f}s")
                time.sleep(wait)
        else:
            logging.warning(f"  ❌ Giving up on page {page} after {max_attempts} attempts")

        # No polite sleep — async path handles rate limiting via semaphore
        return page, page_cars
    except Exception as e:
        logging.exception(f"  ❌ Error on page {page} : {e}")
        return page, []


# ─── Async fetcher (fast network IO) ───────────────────────────────────────────
async def _fetch_page_async(client: httpx.AsyncClient, page: int, sem: asyncio.Semaphore):
    url = f"{SEARCH_URL}?page={page}"
    async with sem:
        max_attempts = 3         # 3 async attempts before handing off to sync fallback
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code != 200:
                    raise Exception(f"Status {resp.status_code}")
                html = resp.text
                if not html or len(html) < 500:
                    raise Exception("Short HTML")
                return page, html
            except Exception as e:
                wait = (2 ** (attempt - 1)) + random.uniform(0, 1.0)  # 1s, 2s, ...
                logging.info(f"  Async page {page} attempt {attempt}/{max_attempts}: {e}; retry in {wait:.1f}s")
                await asyncio.sleep(wait)
        logging.warning(f"  Async giving up on page {page} after {max_attempts} attempts (sync fallback will handle it)")
        return page, None


async def _fetch_pages_async(num_pages: int, concurrency: int = 10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    limits = httpx.Limits(max_keepalive_connections=concurrency, max_connections=concurrency + 5)
    # 25s read timeout: generous enough that slow-but-alive pages don't fall through to sync
    timeout = httpx.Timeout(25.0, connect=8.0)
    async with httpx.AsyncClient(headers=headers, timeout=timeout, limits=limits, http2=False) as client:
        sem = asyncio.Semaphore(concurrency)
        tasks = [asyncio.create_task(_fetch_page_async(client, p, sem)) for p in range(1, num_pages + 1)]
        results = await asyncio.gather(*tasks)
        return {page: html for page, html in results}


def scrape_cars(num_pages: int = 5) -> pd.DataFrame:
    """Orchestrates the scraping of multiple pages using a high-concurrency engine.

    Uses a modern hybrid architecture:
    1. Async I/O (httpx) to fetch all HTML pages simultaneously.
    2. Threaded Parsing (BS4/lxml) to process those pages in parallel.
    3. Infinite Retry Fallback: Any page that fails async fetch is automatically
       retried synchronously until data is retrieved.

    Args:
        num_pages: The number of pages to scrape starting from page 1.

    Returns:
        A pandas DataFrame containing all scraped listings.
    """
    all_cars = []
    seen_links = set()
    # ⚠️  automobile.tn throttles above ~10 concurrent connections.
    # Keeping at 10 ensures near-zero async failures and avoids the costly sync fallback path.
    concurrency = min(10, max(2, num_pages))

    _t_total = time.time()
    print(f"\n{'='*55}")
    print(f"  SCRAPER STARTED — {num_pages} page(s)  |  {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Concurrency: {concurrency} workers")
    print(f"{'='*55}")

    # ── Phase 1: Async HTTP fetch ────────────────────────────────────────────
    try:
        _t_fetch = time.time()
        print(f"  [1/2] Fetching pages...", flush=True)
        pages_html = asyncio.run(_fetch_pages_async(num_pages, concurrency=concurrency))
        _fetch_elapsed = time.time() - _t_fetch
        print(f"  [1/2] Fetch complete — {_fetch_elapsed:.1f}s ({num_pages} pages)")

        # ── Phase 2: Concurrent HTML parsing ────────────────────────────────

        _t_parse = time.time()
        print(f"  [2/2] Parsing pages...", flush=True)
        page_items = list(pages_html.items())
        _pages_ok = 0
        _pages_fallback = 0
        _pages_failed = 0

        def _parse_page(page_html_tuple):
            page, html = page_html_tuple
            page_cars = []
            _pt = time.time()
            if not html:
                # Async gave up — retry sync until we get data (no page left behind)
                attempt = 0
                while not page_cars:
                    attempt += 1
                    _, page_cars = scrape_single_page(page)
                    if page_cars:
                        break
                    wait = min(5.0 * attempt, 30.0)  # 5s, 10s, 15s … capped at 30s
                    print(f"    page {page:>3}/{num_pages}  [RETRY #{attempt}]  waiting {wait:.0f}s before next attempt...")
                    time.sleep(wait)
                elapsed = time.time() - _pt
                print(f"    page {page:>3}/{num_pages}  [RECOVERED after {attempt} attempt(s)]  {elapsed:.1f}s  {len(page_cars)} listings")
                return page, page_cars, "FALLBACK"
            try:
                cards = _extract_cards_from_html(html)
                if cards:
                    for item in cards:
                        car = extract_car(item)
                        if car:
                            page_cars.append(car)
            except Exception as e:
                logging.exception(f"  Parsing error on page {page}: {e}")
            return page, page_cars, "OK"

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(_parse_page, it): it[0] for it in page_items}
            for future in concurrent.futures.as_completed(futures):
                page, page_cars, status = future.result()
                added_count = 0
                if page_cars:
                    for car in page_cars:
                        link = car.get("link", "N/A")
                        if link != "N/A" and link not in seen_links:
                            seen_links.add(link)
                            all_cars.append(car)
                            added_count += 1
                    if status == "OK":
                        _pages_ok += 1
                        print(f"    page {page:>3}/{num_pages}  +{added_count:<4} listings  (total: {len(all_cars)})")
                    elif status == "FALLBACK":
                        _pages_fallback += 1
                        # already printed inside _parse_page
                else:
                    _pages_failed += 1
                    if status == "OK":
                        print(f"    page {page:>3}/{num_pages}  [EMPTY]")
        _parse_elapsed = time.time() - _t_parse
        _fallback_info = f", {_pages_fallback} via fallback" if _pages_fallback else ""
        _failed_info   = f", {_pages_failed} FAILED" if _pages_failed else ""
        print(f"  [2/2] Parse complete — {_parse_elapsed:.1f}s ({_pages_ok} ok{_fallback_info}{_failed_info})")

    except RuntimeError as re_err:
        logging.warning(f"Async unavailable ({re_err}); falling back to threaded requests.")
        _t_parse = time.time()
        max_workers = min(8, max(2, num_pages))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(scrape_single_page, p): p for p in range(1, num_pages + 1)}
            for future in concurrent.futures.as_completed(futures):
                page, page_cars = future.result()
                added_count = 0
                if page_cars:
                    for car in page_cars:
                        link = car.get("link", "N/A")
                        if link != "N/A" and link not in seen_links:
                            seen_links.add(link)
                            all_cars.append(car)
                            added_count += 1
                    print(f"    page {page:>3}/{num_pages}  +{added_count:<4} listings  (total so far: {len(all_cars)})")
                else:
                    print(f"    page {page:>3}/{num_pages}  no listings")
        _parse_elapsed = time.time() - _t_parse

    # ── Final summary ────────────────────────────────────────────────────────
    _total_elapsed = time.time() - _t_total
    _mins, _secs = divmod(int(_total_elapsed), 60)
    _time_str = f"{_mins}m {_secs}s" if _mins else f"{_secs:.1f}s"
    _rate = f"{len(all_cars) / _total_elapsed:.1f}" if _total_elapsed > 0 and all_cars else "0"
    _avg_per_page = f"{_total_elapsed / num_pages:.1f}" if num_pages else "0"

    df = pd.DataFrame(all_cars, columns=EXPECTED_COLUMNS)
    print(f"\n{'='*55}")
    print(f"  SCRAPE COMPLETE")
    print(f"  Total time   : {_time_str}")
    print(f"  Listings     : {len(df)}")
    print(f"  Rate         : {_rate} listings/sec")
    print(f"  Avg/page     : {_avg_per_page}s")
    print(f"  Finished at  : {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*55}\n")
    return df



# ─── Persistance SQLite ────────────────────────────────────────────────────────
import sqlite3
import json

def get_last_sync_time(meta_path: str = "data/metadata.json") -> dict:
    """Récupère l'état complet de la synchronisation (temps + lock)."""
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
                dt = datetime.fromisoformat(data.get("last_sync")) if data.get("last_sync") else datetime.min
                return {"last_sync": dt, "is_syncing": data.get("is_syncing", False)}
        except Exception:
            pass
    return {"last_sync": datetime.min, "is_syncing": False}

def set_sync_lock(status: bool, meta_path: str = "data/metadata.json"):
    """Active ou désactive le verrou de synchronisation globale."""
    os.makedirs(os.path.dirname(meta_path), exist_ok=True)
    data = {"last_sync": datetime.min.isoformat(), "is_syncing": status}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                data = json.load(f)
        except Exception:
            pass
    
    data["is_syncing"] = status
    if not status: # If we are unlocking, we usually just finished a sync
        data["last_sync"] = datetime.now().isoformat()

    with open(meta_path, "w") as f:
        json.dump(data, f)

def update_last_sync_time(meta_path: str = "data/metadata.json"):
    """Met à jour l'horodatage de la synchronisation et libère le verrou."""
    set_sync_lock(False, meta_path)

def save_data(df: pd.DataFrame, db_path: str = "data/cars.db") -> pd.DataFrame:
    """Saves listings to a SQLite database with historic price tracking.

    Maintains two tables:
    - `cars`: The latest snapshot of each unique car (keyed by link).
    - `price_history`: An append-only log of every price observation for history.

    Args:
        df: The DataFrame to save.
        db_path: Path to the SQLite database.

    Returns:
        A merged DataFrame representing the updated current state.
    """
    os.makedirs("data", exist_ok=True)

    if df.empty:
        print("⚠️  No data to save.")
        return df

    conn = sqlite3.connect(db_path)
    try:
        # Pre-process prices for history
        df["price"] = pd.to_numeric(df["price_raw"].str.replace(r"[^\d]", "", regex=True), errors="coerce")
        
        # 1. Update Price History Table (Global Archive)
        history_entry = df[["link", "price", "scraped_at"]].dropna(subset=["price"])
        history_entry.to_sql("price_history", conn, if_exists="append", index=False)
        
        # 2. Update Main Cars Table (Latest Snapshot)
        try:
            existing = pd.read_sql("SELECT * FROM cars", conn)
            df_merged = pd.concat([existing, df], ignore_index=True)
            # We keep the LATEST scraping for each link to show the current state
            df_merged = df_merged.drop_duplicates(subset=["link"], keep="last")
            df_merged.to_sql("cars", conn, if_exists="replace", index=False)
            print(f"💾 Data saved → {db_path}  ({len(df_merged)} unique listings)")
            update_last_sync_time()
            return df_merged
        except Exception:
            # Table doesn't exist yet
            df.to_sql("cars", conn, if_exists="replace", index=False)
            print(f"💾 Data initialized → {db_path}  ({len(df)} rows)")
            update_last_sync_time()
            return df
            
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return df
    finally:
        conn.close()


def load_data(db_path: str = "data/cars.db") -> pd.DataFrame:
    """Loads the current car snapshot from the SQLite database."""
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        try:
            df = pd.read_sql("SELECT * FROM cars", conn)
            print(f"📂 Data loaded — {len(df)} rows")
            return df
        except Exception:
            pass
        finally:
            conn.close()
            
    print("⚠️  No database found.")
    return pd.DataFrame()


# ─── Test rapide ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df_raw = scrape_cars(num_pages=3)
    if not df_raw.empty:
        save_data(df_raw)
        print(df_raw.head())
