"""
analyzer.py — Analyse statistique des données automobiles
"""

import pandas as pd
import numpy as np


# ─── Statistiques générales ───────────────────────────────────────────────────

def get_price_stats(df: pd.DataFrame) -> dict:
    """Retourne les statistiques descriptives du prix."""
    prices = df["price"].dropna()
    if prices.empty:
        return {}
    return {
        "count":   int(prices.count()),
        "min":     round(prices.min(), 0),
        "max":     round(prices.max(), 0),
        "mean":    round(prices.mean(), 0),
        "median":  round(prices.median(), 0),
        "std":     round(prices.std(), 0),
        "q25":     round(prices.quantile(0.25), 0),
        "q75":     round(prices.quantile(0.75), 0),
    }


def get_km_stats(df: pd.DataFrame) -> dict:
    """Retourne les statistiques descriptives du kilométrage."""
    kms = df["km"].dropna()
    if kms.empty:
        return {}
    return {
        "count":   int(kms.count()),
        "min":     round(kms.min(), 0),
        "max":     round(kms.max(), 0),
        "mean":    round(kms.mean(), 0),
        "median":  round(kms.median(), 0),
    }


def get_year_stats(df: pd.DataFrame) -> dict:
    """Retourne les statistiques descriptives de l'année."""
    years = df["year"].dropna()
    if years.empty:
        return {}
    return {
        "oldest":  int(years.min()),
        "newest":  int(years.max()),
        "mean":    round(years.mean(), 1),
        "median":  int(years.median()),
    }


# ─── Top / Bottom 5 ──────────────────────────────────────────────────────────

def top5_expensive(df: pd.DataFrame) -> pd.DataFrame:
    """Top 5 voitures les plus chères."""
    return (
        df.dropna(subset=["price"])
        .nlargest(5, "price")[["title", "brand", "year", "price", "km", "fuel", "location"]]
    )


def bottom5_cheapest(df: pd.DataFrame) -> pd.DataFrame:
    """Top 5 voitures les moins chères (prix > 0)."""
    return (
        df[df["price"] > 0].dropna(subset=["price"])
        .nsmallest(5, "price")[["title", "brand", "year", "price", "km", "fuel", "location"]]
    )


def top5_newest(df: pd.DataFrame) -> pd.DataFrame:
    """Top 5 voitures les plus récentes."""
    return (
        df.dropna(subset=["year"])
        .nlargest(5, "year")[["title", "brand", "year", "price", "km", "fuel", "location"]]
    )


def top5_low_km(df: pd.DataFrame) -> pd.DataFrame:
    """Top 5 voitures avec le moins de kilométrage."""
    return (
        df[df["km"] > 0].dropna(subset=["km"])
        .nsmallest(5, "km")[["title", "brand", "year", "price", "km", "fuel", "location"]]
    )


# ─── Distributions ────────────────────────────────────────────────────────────

def by_brand(df: pd.DataFrame) -> pd.DataFrame:
    """Number of listings and avg price per brand."""
    return (
        df.groupby("brand")
        .agg(
            num_listings=("title", "count"),
            avg_price=("price", lambda x: round(x.mean(), 0)),
            avg_km=("km", lambda x: round(x.mean(), 0)),
        )
        .sort_values("num_listings", ascending=False)
        .reset_index()
    )


def by_fuel(df: pd.DataFrame) -> pd.DataFrame:
    """Distribution by fuel type."""
    return (
        df.groupby("fuel")
        .agg(num_listings=("title", "count"), avg_price=("price", "mean"))
        .sort_values("num_listings", ascending=False)
        .reset_index()
    )


def by_location(df: pd.DataFrame) -> pd.DataFrame:
    """Distribution by location/region."""
    return (
        df.groupby("location")
        .agg(num_listings=("title", "count"), avg_price=("price", "mean"))
        .sort_values("num_listings", ascending=False)
        .head(15)
        .reset_index()
    )


def by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Average price by manufacturing year."""
    return (
        df.dropna(subset=["year", "price"])
        .groupby("year")
        .agg(
            num_listings=("title", "count"),
            avg_price=("price", lambda x: round(x.mean(), 0)),
        )
        .sort_values("year")
        .reset_index()
    )


def price_distribution_bins(df: pd.DataFrame, bins: int = 10) -> pd.DataFrame:
    """Distribution of prices by tiers."""
    prices = df["price"].dropna()
    if prices.empty:
        return pd.DataFrame()
    cut, labels = pd.cut(prices, bins=bins, retbins=True)
    result = cut.value_counts().sort_index().reset_index()
    result.columns = ["price_tier", "num_listings"]
    result["price_tier"] = result["price_tier"].astype(str)
    return result


# ─── Résumé complet ───────────────────────────────────────────────────────────

def full_summary(df: pd.DataFrame) -> dict:
    """Generates a complete analysis report."""
    return {
        "total_listings":    len(df),
        "with_price":        int(df["price"].notna().sum()),
        "unique_brands":     int(df["brand"].nunique()),
        "unique_villes":     int(df["location"].nunique()),
        "price_stats":       get_price_stats(df),
        "km_stats":          get_km_stats(df),
        "year_stats":        get_year_stats(df),
        "top5_expensive":    top5_expensive(df),
        "bottom5_cheapest":  bottom5_cheapest(df),
        "top5_newest":       top5_newest(df),
        "top5_low_km":       top5_low_km(df),
        "by_brand":          by_brand(df),
        "by_fuel":           by_fuel(df),
        "by_location":       by_location(df),
        "by_year":           by_year(df),
    }


if __name__ == "__main__":
    # Test avec données fictives
    import json
    sample = pd.DataFrame({
        "title": ["Toyota Corolla", "Peugeot 208", "VW Golf", "Renault Clio", "BMW Serie 3"],
        "brand": ["Toyota", "Peugeot", "Volkswagen", "Renault", "BMW"],
        "year":  [2019, 2021, 2018, 2020, 2017],
        "price": [15000, 28500, 22000, 18000, 35000],
        "km":    [80000, 35000, 95000, 60000, 110000],
        "fuel":  ["Diesel", "Essence", "Diesel", "Essence", "Diesel"],
        "location": ["Tunis", "Sfax", "Tunis", "Sousse", "Tunis"],
    })
    summary = full_summary(sample)
    print("── Prix ──")
    print(json.dumps(summary["price_stats"], indent=2))
    print("\n── Top 5 chers ──")
    print(summary["top5_expensive"])
