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
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

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
    "scraped_at",
]

# ─── Extraction d'une annonce ──────────────────────────────────────────────────

def _setup_driver(headless: bool = True):
    """Crée un navigateur Selenium avec fallback Chrome -> Edge (Windows)."""
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--lang=fr-FR")
    chrome_options.add_argument(f"--user-agent={ua}")

    # Aide Selenium à trouver chrome sur Windows si installé hors PATH.
    possible_chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in possible_chrome_paths:
        if path and os.path.exists(path):
            chrome_options.binary_location = path
            break

    edge_options = EdgeOptions()
    if headless:
        edge_options.add_argument("--headless=new")
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument("--window-size=1920,1080")
    edge_options.add_argument("--lang=fr-FR")
    edge_options.add_argument(f"--user-agent={ua}")

    # 1) Selenium Manager local auto-discovery (pas de dependency forte au réseau).
    try:
        print("🌐 Navigateur Selenium: Chrome (Selenium Manager)")
        return webdriver.Chrome(options=chrome_options)
    except Exception:
        pass

    try:
        print("🌐 Navigateur Selenium: Edge (Selenium Manager)")
        return webdriver.Edge(options=edge_options)
    except Exception:
        pass

    # 2) Fallback webdriver-manager si téléchargement autorisé.
    try:
        chrome_service = Service(ChromeDriverManager().install())
        print("🌐 Navigateur Selenium: Chrome (webdriver-manager)")
        return webdriver.Chrome(service=chrome_service, options=chrome_options)
    except Exception:
        edge_service = EdgeService(EdgeChromiumDriverManager().install())
        print("🌐 Navigateur Selenium: Edge (webdriver-manager)")
        return webdriver.Edge(service=edge_service, options=edge_options)


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

        return {
            "title": title,
            "price_raw": price_raw,
            "year_raw": year_raw,
            "km_raw": km_raw,
            "fuel": fuel,
            "location": location,
            "link": link,
            "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        print(f"  ⚠️  Erreur extraction d'une annonce : {e}")
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

def scrape_cars(num_pages: int = 5) -> pd.DataFrame:
    """
    Parcourt `num_pages` pages d'annonces et retourne un DataFrame brut.
    """
    all_cars = []
    seen_links = set()
    print(f"🚗 Début du scraping — {num_pages} page(s)…\n")

    driver = None
    try:
        driver = _setup_driver(headless=True)

        for page in range(1, num_pages + 1):
            url = f"{SEARCH_URL}?page={page}"
            try:
                driver.get(url)
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )

                # Attendre le rendu JS et la population des annonces.
                time.sleep(2)

                cards = _extract_cards_from_html(driver.page_source)
                if not cards:
                    print(f"  ℹ️  Aucune annonce détectée page {page} — arrêt pagination.")
                    break

                page_count = 0
                for item in cards:
                    car = extract_car(item)
                    if not car:
                        continue

                    link = car.get("link", "N/A")
                    if link != "N/A" and link in seen_links:
                        continue

                    if link != "N/A":
                        seen_links.add(link)
                    all_cars.append(car)
                    page_count += 1

                print(
                    f"  ✅ Page {page}/{num_pages} — {page_count} nouvelles annonces "
                    f"({len(all_cars)} total)"
                )

                # Délai demandé entre pages.
                time.sleep(2)

            except Exception as e:
                print(f"  ❌ Erreur page {page} : {e}")

    except Exception as e:
        print(f"  ❌ Impossible d'initialiser Selenium : {e}")
    finally:
        if driver:
            driver.quit()

    df = pd.DataFrame(all_cars, columns=EXPECTED_COLUMNS)
    print(f"\n📦 Scraping terminé — {len(df)} annonces collectées au total.")
    return df


# ─── Persistance CSV ──────────────────────────────────────────────────────────

def save_data(df: pd.DataFrame, filepath: str = DATA_PATH) -> pd.DataFrame:
    """Sauvegarde le DataFrame (fusionne avec les données existantes)."""
    os.makedirs("data", exist_ok=True)

    if df.empty:
        print("⚠️  Aucune donnée à sauvegarder.")
        return df

    if os.path.exists(filepath):
        existing = pd.read_csv(filepath)
        df = pd.concat([existing, df], ignore_index=True).drop_duplicates(
            subset=["title", "price_raw", "link"], keep="last"
        )

    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    print(f"💾 Données sauvegardées → {filepath}  ({len(df)} lignes)")
    return df


def load_data(filepath: str = DATA_PATH) -> pd.DataFrame:
    """Charge les données depuis le CSV."""
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        print(f"📂 Données chargées — {len(df)} lignes")
        return df
    print("⚠️  Aucun fichier de données trouvé.")
    return pd.DataFrame()


# ─── Test rapide ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    df_raw = scrape_cars(num_pages=3)
    if not df_raw.empty:
        save_data(df_raw)
        print(df_raw.head())
