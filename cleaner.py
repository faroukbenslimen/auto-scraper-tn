"""
cleaner.py — Nettoyage et structuration des données automobiles
"""

import pandas as pd
import numpy as np
import re

# ─── Fonctions de nettoyage atomiques ─────────────────────────────────────────

def clean_price(value: str) -> float:
    """Converts a raw price string into a float.

    Handles common Tunisian formatting artifacts like 'DT', 'TND', 'DINARS',
    and variations in thousands/decimal separators.

    Args:
        value: The raw price string (e.g., '15 000 DT', '15.000').

    Returns:
        The cleaned price as a float, or np.nan if conversion fails.
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
    """Extracts a valid automotive year from a raw string.

    Looks for four-digit years between 1980 and 2025.

    Args:
        value: The raw year string (e.g., 'Année : 2019', '2 019').

    Returns:
        A float representing the year, or np.nan if not found.
    """
    try:
        if pd.isna(value) or str(value).strip() in ("N/A", "", "-"):
            return np.nan
        match = re.search(r"(19[89]\d|20[012]\d)", str(value).replace(" ", ""))
        return float(match.group(1)) if match else np.nan
    except Exception:
        return np.nan


def clean_km(value: str) -> float:
    """Converts a raw mileage string into a float.

    Arg:
        value: Raw mileage string (e.g., '120 000 km').

    Returns:
        Total kilometers as a float, or np.nan if conversion fails.
    """
    try:
        if pd.isna(value) or str(value).strip() in ("N/A", "", "-"):
            return np.nan
        digits = re.sub(r"[^\d]", "", str(value))
        return float(digits) if digits else np.nan
    except Exception:
        return np.nan


def extract_brand(title: str) -> str:
    """Identifies the car manufacturer brand from the listing title.

    Matches against a predefined list of brands common in the Tunisian market.
    Defaults to the first word of the title if no known brand is found.

    Args:
        title: listing title (e.g., 'Toyota Corolla 2019').

    Returns:
        The identified brand name or 'Other'.
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
    """Normalizes the fuel type category."""
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
    """Normalizes the geographical location string."""
    cleaned = re.sub(r"\s+", " ", str(value)).strip()
    return cleaned if cleaned not in ("N/A", "", "nan") else "Not specified"


# ─── Pipeline principal ────────────────────────────────────────────────────────

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Applies the full cleaning and normalization pipeline to a DataFrame.

    This function handles both raw scraped data (slow path) and previously
    cleansed database data (fast path). It extracts year, mileage, and brand
    information, computes vehicle age, and removes duplicates.

    Args:
        df: Input DataFrame containing raw or partially cleaned data.

    Returns:
        A cleaned DataFrame with normalized numeric columns and standard types.
    """
    if df.empty:
        return df

    df = df.copy()
    is_already_clean = (
        "price" in df.columns
        and pd.api.types.is_numeric_dtype(df["price"])
        and df["price"].notna().mean() > 0.7  # at least 70% have valid prices
    )

    if is_already_clean:
        # ── Fast path: data from DB ──────────────────────────────────────────
        # Price is already numeric. Extract year/km with fast vectorized regex
        # instead of the slow row-by-row apply() calls.

        if "year" not in df.columns and "year_raw" in df.columns:
            # Vectorized year extraction — single regex pass on the whole column
            df["year"] = pd.to_numeric(
                df["year_raw"].astype(str).str.extract(r"(19[89]\d|20[012]\d)")[0],
                errors="coerce"
            )

        if "km" not in df.columns and "km_raw" in df.columns:
            # Vectorized km extraction — strip non-digits, convert to float
            df["km"] = pd.to_numeric(
                df["km_raw"].astype(str).str.replace(r"[^\d]", "", regex=True),
                errors="coerce"
            )

        if "brand" not in df.columns and "title" in df.columns:
            df["brand"] = df["title"].apply(extract_brand)

        current_year = 2025
        if "year" in df.columns and "age" not in df.columns:
            df["age"] = pd.to_numeric(current_year - df["year"], errors="coerce")
            df.loc[~df["age"].between(0, 60), "age"] = np.nan

        if "fuel" in df.columns:
            df["fuel"] = df["fuel"].apply(clean_fuel)
        if "location" in df.columns:
            df["location"] = df["location"].apply(clean_location)

        # Drop raw columns (they're no longer needed)
        df.drop(columns=["price_raw", "year_raw", "km_raw"], errors="ignore", inplace=True)

        before = len(df)
        df.drop_duplicates(subset=["title", "price"], inplace=True)
        removed = before - len(df)
        if removed:
            print(f"  [Cleaner] Fast path: removed {removed} duplicate(s)")

        cols_order = ["title", "brand", "year", "age", "price", "km", "fuel",
                      "location", "link", "scraped_at", "image_url"]
        existing = [c for c in cols_order if c in df.columns]
        extra = [c for c in df.columns if c not in existing]
        df = df[existing + extra]
        print(f"  [Cleaner] Fast path complete — {len(df)} rows")
        return df


    # ── Full cleaning path: raw scraped data ────────────────────────────────
    print("[Cleaner] Running full pipeline...")
    df["price"]    = df["price_raw"].apply(clean_price)
    df["year"]     = df["year_raw"].apply(clean_year)
    df["km"]       = df["km_raw"].apply(clean_km)
    df["brand"]    = df["title"].apply(extract_brand)
    df["fuel"]     = df["fuel"].apply(clean_fuel)
    df["location"] = df["location"].apply(clean_location)

    current_year = 2025
    df["age"] = current_year - df["year"]
    df.loc[~df["age"].between(0, 60), "age"] = np.nan

    df.drop(columns=["price_raw", "year_raw", "km_raw"], errors="ignore", inplace=True)

    before = len(df)
    df.drop_duplicates(subset=["title", "price"], inplace=True)
    print(f"  [Cleaner] Removed {before - len(df)} duplicate(s)")

    cols_order = ["title", "brand", "year", "age", "price", "km", "fuel", "location", "link", "scraped_at", "image_url"]
    existing = [c for c in cols_order if c in df.columns]
    extra = [c for c in df.columns if c not in existing]
    df = df[existing + extra]

    total_valid = int(df["price"].notna().sum())
    print(f"  [Cleaner] {total_valid}/{len(df)} with valid price — complete")
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
