"""
cleaner.py — Nettoyage et structuration des données automobiles
"""

import pandas as pd
import numpy as np
import re

# ─── Fonctions de nettoyage atomiques ─────────────────────────────────────────

def clean_price(value: str) -> float:
    """
    Convertit une chaîne prix en float.
    Ex : "15 000 DT" → 15000.0 | "15.000" → 15000.0 | "N/A" → NaN
    """
    try:
        if pd.isna(value) or str(value).strip() in ("N/A", "", "-"):
            return np.nan
        # Replace common Tunisian price formatting artifacts
        cleaned = str(value).upper().replace("DT", "").replace("TND", "").replace("DINARS", "")
        cleaned = re.sub(r"[^\d.,]", "", cleaned)
        
        # Gérer le format européen (15.000,00) vs anglais (15,000.00)
        if "," in cleaned and "." in cleaned:
            # Assume last separator is decimal if its 2 digits, otherwise ignore
            parts = cleaned.split(".")
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(",", "").replace(".", ".")
            else:
                cleaned = cleaned.replace(".", "").replace(",", "")
        elif "," in cleaned:
            # In Tunisia, "," is often a decimal for millimes or just a thousands separator
            if len(cleaned.split(",")[-1]) == 3: # Thousands
                cleaned = cleaned.replace(",", "")
            else: # Decimal
                cleaned = cleaned.replace(",", ".")
        elif "." in cleaned:
            if len(cleaned.split(".")[-1]) == 3: # Thousands
                cleaned = cleaned.replace(".", "")
        
        return float(cleaned) if cleaned else np.nan
    except Exception:
        return np.nan


def clean_year(value: str) -> float:
    """
    Extrait une année valide (1980–2025).
    Ex : "Année : 2019" → 2019 | "2 019" → 2019 | "N/A" → NaN
    """
    try:
        if pd.isna(value) or str(value).strip() in ("N/A", "", "-"):
            return np.nan
        match = re.search(r"(19[89]\d|20[012]\d)", str(value).replace(" ", ""))
        return float(match.group(1)) if match else np.nan
    except Exception:
        return np.nan


def clean_km(value: str) -> float:
    """
    Convertit le kilométrage en float.
    Ex : "120 000 km" → 120000.0
    """
    try:
        if pd.isna(value) or str(value).strip() in ("N/A", "", "-"):
            return np.nan
        digits = re.sub(r"[^\d]", "", str(value))
        return float(digits) if digits else np.nan
    except Exception:
        return np.nan


def extract_brand(title: str) -> str:
    """
    Extrait la marque automobile depuis le titre de l'annonce.
    Fonctionne sur les marques courantes en Tunisie.
    """
    KNOWN_BRANDS = [
        "Toyota", "Volkswagen", "Peugeot", "Renault", "Citroën", "Citroen",
        "Ford", "BMW", "Mercedes", "Audi", "Hyundai", "Kia", "Seat",
        "Opel", "Fiat", "Nissan", "Suzuki", "Skoda", "Dacia", "Honda",
        "Mitsubishi", "Mazda", "Chevrolet", "Jeep", "Land Rover", "Range Rover",
        "Alfa Romeo", "Lancia", "Ssangyong", "Mahindra", "Isuzu", "Chery",
        "MG", "Haval", "Dongfeng", "Geely", "Baic", "Great Wall", "Porsche",
        "Jaguar", "Volvo", "Mini", "Smart", "Iveco", "Chery"
    ]
    title_lower = str(title).lower()
    for brand in KNOWN_BRANDS:
        if brand.lower() in title_lower:
            return brand
    # If not found, take the first word
    words = str(title).split()
    return words[0] if words else "Other"


def clean_fuel(value: str) -> str:
    """Normalise le type de carburant."""
    val = str(value).lower().strip()
    if "diesel" in val or "gasoil" in val:
        return "Diesel"
    if "essence" in val or "sans plomb" in val:
        return "Gasoline"
    if "hybride" in val:
        return "Hybrid"
    if "électr" in val or "electr" in val:
        return "Electric"
    if "gpl" in val or "gaz" in val:
        return "LPG"
    return "Not specified"


def clean_location(value: str) -> str:
    """Normalise la localisation (supprime espaces parasites)."""
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned if cleaned not in ("N/A", "", "nan") else "Not specified"


# ─── Pipeline principal ────────────────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique le pipeline de nettoyage complet sur le DataFrame brut.
    Retourne un DataFrame propre avec des colonnes typées.
    """
    if df.empty:
        return df

    print("🧹 Cleaning data…")
    df = df.copy()

    # ── Colonnes numériques ──────────────────────────────────────────────────
    df["price"]    = df["price_raw"].apply(clean_price)
    df["year"]     = df["year_raw"].apply(clean_year)
    df["km"]       = df["km_raw"].apply(clean_km)

    # ── Colonnes catégorielles ───────────────────────────────────────────────
    df["brand"]    = df["title"].apply(extract_brand)
    df["fuel"]     = df["fuel"].apply(clean_fuel)
    df["location"] = df["location"].apply(clean_location)

    # ── Colonne âge du véhicule ──────────────────────────────────────────────
    current_year = 2025
    df["age"] = current_year - df["year"]
    df.loc[df["age"] < 0, "age"] = np.nan
    df.loc[df["age"] > 60, "age"] = np.nan

    # ── Suppression des colonnes brutes ──────────────────────────────────────
    df.drop(columns=["price_raw", "year_raw", "km_raw"], errors="ignore", inplace=True)

    # ── Drop duplicates ─────────────────────────────────────────────
    before = len(df)
    df.drop_duplicates(subset=["title", "price"], inplace=True)
    after = len(df)
    print(f"  → {before - after} duplicate(s) removed")

    # ── Réordonnancement des colonnes ────────────────────────────────────────
    cols_order = ["title", "brand", "year", "age", "price", "km", "fuel", "location", "link", "scraped_at"]
    existing_cols = [c for c in cols_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + extra_cols]

    total_valid = df["price"].notna().sum()
    print(f"  → {total_valid}/{len(df)} listings with valid price")
    print(f"✅ Cleaning complete — {len(df)} clean rows\n")
    return df


# ─── Test rapide ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Données de test
    sample = pd.DataFrame({
        "title": ["Toyota Corolla 2019", "Peugeot 208 2021", "Volkswagen Golf  "],
        "price_raw": ["15 000 DT", "28.500 DT", "N/A"],
        "year_raw": ["2019", "Année 2021", "2018"],
        "km_raw": ["80 000 km", "35 000 km", "120000"],
        "fuel": ["diesel", "essence", "Diesel"],
        "location": ["Tunis", "Sfax  ", "N/A"],
        "link": ["/annonce/1", "/annonce/2", "/annonce/3"],
        "scraped_at": ["2025-01-01"] * 3,
    })
    df_clean = clean_dataframe(sample)
    print(df_clean)
