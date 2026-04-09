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
    """Extrait les données d'un bloc HTML d'annonce voiture rendu dynamiquement."""
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
    """Construit une liste de conteneurs annonces depuis le DOM rendu."""
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
    """Scrapes a single page and returns the parsed cards efficiently via HTTP."""
    url = f"{SEARCH_URL}?page={page}"
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"})
        if response.status_code != 200:
            print(f"  ❌ Failed to load page {page} — Status {response.status_code}")
            return []
        
        cards = _extract_cards_from_html(response.text)
        page_cars = []
        if cards:
            for item in cards:
                car = extract_car(item)
                if car:
                    page_cars.append(car)
        return page, page_cars
    except Exception as e:
        print(f"  ❌ Error on page {page} : {e}")
        return page, []

def scrape_cars(num_pages: int = 5) -> pd.DataFrame:
    """
    Parcourt `num_pages` pages d'annonces en multi-threading super-rapide.
    """
    all_cars = []
    seen_links = set()
    print(f"🚀 Starting TURBO Scraping — {num_pages} page(s) over concurrent threads…\n")

    # Utiliser 10-20 workers pour lancer les requêtes HTTP simultanément
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
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
                print(f"  ✅ Thread {page}/{num_pages} finished — {added_count} new listings")
            else:
                print(f"  ℹ️ Thread {page}/{num_pages} — No listings detected.")

    df = pd.DataFrame(all_cars, columns=EXPECTED_COLUMNS)
    print(f"\n📦 Scraping complete — {len(df)} listings collected in total.")
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
    """Sauvegarde le DataFrame dans une base SQLite avec suivi historique."""
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
    """Charge les données depuis la base SQLite."""
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
