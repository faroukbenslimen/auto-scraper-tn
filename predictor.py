"""
predictor.py — Partie IA / Prédiction de prix automobiles

Deux modèles :
  1. Prédiction de prix par caractéristiques (Random Forest)
  2. Tendance temporelle du prix moyen (régression linéaire)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import warnings
warnings.filterwarnings("ignore")


# ─── Modèle 1 : Prédiction par caractéristiques ───────────────────────────────

class CarPricePredictor:
    """Prédit le prix d'une voiture à partir de ses caractéristiques."""

    def __init__(self):
        self.model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.label_encoders = {}
        self.feature_names = ["year", "km", "brand", "fuel"]
        self.is_trained = False
        self.metrics = {}

    def _encode(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Encode les variables catégorielles."""
        df = df.copy()
        for col in ["brand", "fuel"]:
            if col in df.columns:
                if fit:
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str).fillna("Autre"))
                    self.label_encoders[col] = le
                else:
                    le = self.label_encoders.get(col)
                    if le:
                        def safe_transform(val):
                            try:
                                return le.transform([str(val)])[0]
                            except ValueError:
                                return 0  # catégorie inconnue
                        df[col] = df[col].astype(str).fillna("Autre").apply(safe_transform)
        return df

    def train(self, df: pd.DataFrame) -> dict:
        """Entraîne le modèle sur les données propres."""
        required = ["price", "year", "km", "brand", "fuel"]
        df_model = df[required].dropna().copy()

        if len(df_model) < 10:
            return {"error": "Pas assez de données pour l'entraînement (minimum 10 lignes)."}

        df_model = self._encode(df_model, fit=True)
        X = df_model[["year", "km", "brand", "fuel"]]
        y = df_model["price"]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        self.model.fit(X_train, y_train)

        y_pred = self.model.predict(X_test)
        self.metrics = {
            "mae":   round(mean_absolute_error(y_test, y_pred), 0),
            "r2":    round(r2_score(y_test, y_pred), 3),
            "train_size": len(X_train),
            "test_size":  len(X_test),
        }
        self.is_trained = True

        importances = pd.Series(
            self.model.feature_importances_, index=["year", "km", "brand", "fuel"]
        ).sort_values(ascending=False)
        self.metrics["feature_importance"] = importances.to_dict()

        print(f"✅ Modèle entraîné — MAE: {self.metrics['mae']:,.0f} DT | R²: {self.metrics['r2']}")
        return self.metrics

    def predict(self, year: int, km: int, brand: str, fuel: str) -> float:
        """Retourne le prix estimé pour une voiture donnée."""
        if not self.is_trained:
            raise RuntimeError("Le modèle n'est pas encore entraîné.")

        input_df = pd.DataFrame([{"year": year, "km": km, "brand": brand, "fuel": fuel}])
        input_df = self._encode(input_df, fit=False)
        price = self.model.predict(input_df[["year", "km", "brand", "fuel"]])[0]
        return round(max(price, 0), 0)

    def predict_range(self, year: int, km: int, brand: str, fuel: str) -> dict:
        """Retourne le prix estimé avec une fourchette (±std des arbres)."""
        if not self.is_trained:
            raise RuntimeError("Le modèle n'est pas encore entraîné.")

        input_df = pd.DataFrame([{"year": year, "km": km, "brand": brand, "fuel": fuel}])
        input_df = self._encode(input_df, fit=False)
        X = input_df[["year", "km", "brand", "fuel"]]

        tree_preds = np.array([tree.predict(X)[0] for tree in self.model.estimators_])
        return {
            "predicted":  round(np.mean(tree_preds), 0),
            "low":        round(max(np.percentile(tree_preds, 10), 0), 0),
            "high":       round(np.percentile(tree_preds, 90), 0),
            "confidence": round(1 - (np.std(tree_preds) / (np.mean(tree_preds) + 1e-6)), 2),
        }


# ─── Modèle 2 : Tendance du prix moyen dans le temps ─────────────────────────

class PriceTrendPredictor:
    """
    Analyse la tendance du prix moyen et prédit les N prochains jours.
    Utilise une régression linéaire sur les données historiques agrégées.
    """

    def __init__(self):
        self.model = LinearRegression()
        self.is_trained = False
        self.last_date = None
        self.history = None

    def prepare_timeseries(self, df: pd.DataFrame) -> pd.DataFrame:
        """Agrège les prix par date de scraping."""
        df = df.copy()
        df["scraped_at"] = pd.to_datetime(df["scraped_at"], errors="coerce")
        df["date"] = df["scraped_at"].dt.date

        ts = (
            df.dropna(subset=["price"])
            .groupby("date")
            .agg(prix_moyen=("price", "mean"), nb_annonces=("price", "count"))
            .reset_index()
            .sort_values("date")
        )
        ts["prix_moyen"] = ts["prix_moyen"].round(0)
        return ts

    def train(self, df: pd.DataFrame) -> dict:
        """Entraîne le modèle de tendance temporelle."""
        ts = self.prepare_timeseries(df)
        self.history = ts

        if len(ts) < 2:
            # Pas assez de points temporels → simulation de tendance
            print("⚠️  Données d'une seule session — simulation de tendance activée.")
            self._simulate_trend(df)
            return {"simulated": True, "points": len(ts)}

        ts["t"] = (pd.to_datetime(ts["date"]) - pd.to_datetime(ts["date"].min())).dt.days
        X = ts["t"].values.reshape(-1, 1)
        y = ts["prix_moyen"].values

        self.model.fit(X, y)
        self.last_t = ts["t"].max()
        self.base_date = pd.to_datetime(ts["date"].min())
        self.is_trained = True

        slope = round(self.model.coef_[0], 2)
        trend = "📈 Hausse" if slope > 0 else "📉 Baisse"
        print(f"✅ Tendance détectée : {trend} ({slope:+.2f} DT/jour)")
        return {"slope": slope, "trend": trend, "data_points": len(ts)}

    def _simulate_trend(self, df: pd.DataFrame):
        """Simule une tendance sur 30 jours en ajoutant du bruit."""
        base_price = df["price"].dropna().mean()
        dates = pd.date_range(end=pd.Timestamp.today(), periods=30, freq="D")
        noise = np.random.normal(0, base_price * 0.02, 30).cumsum()
        simulated = pd.DataFrame({
            "date": dates.date,
            "prix_moyen": (base_price + noise).round(0),
            "nb_annonces": np.random.randint(5, 30, 30),
        })
        self.history = simulated
        self.is_trained = False  # Modèle non entraîné mais historique disponible

    def predict_future(self, days: int = 7) -> pd.DataFrame:
        """Prédit le prix moyen pour les N prochains jours."""
        if not self.is_trained:
            # Extrapolation simple à partir du dernier prix connu
            last_price = float(self.history["prix_moyen"].iloc[-1])
            last_date = pd.to_datetime(self.history["date"].iloc[-1])
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
            variation = np.linspace(0, last_price * 0.03, days)  # +3% sur la période
            return pd.DataFrame({
                "date":       future_dates.date,
                "prix_predit": (last_price + variation).round(0),
                "type":       "Prédiction",
            })

        future_t = np.arange(self.last_t + 1, self.last_t + days + 1)
        prices = self.model.predict(future_t.reshape(-1, 1))
        future_dates = [
            (self.base_date + pd.Timedelta(days=int(t))).date() for t in future_t
        ]
        return pd.DataFrame({
            "date":        future_dates,
            "prix_predit": prices.round(0),
            "type":        "Prédiction",
        })

    def get_full_history_with_prediction(self, days: int = 7) -> pd.DataFrame:
        """Retourne l'historique + la prédiction dans un seul DataFrame."""
        hist = self.history.copy()
        hist = hist.rename(columns={"prix_moyen": "prix_predit"})
        hist["type"] = "Historique"

        future = self.predict_future(days)

        return pd.concat([hist[["date", "prix_predit", "type"]], future], ignore_index=True)


# ─── Test rapide ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample = pd.DataFrame({
        "title": ["Toyota Corolla", "Peugeot 208", "VW Golf", "Renault Clio", "BMW 3"],
        "brand": ["Toyota", "Peugeot", "Volkswagen", "Renault", "BMW"],
        "year":  [2019, 2021, 2018, 2020, 2017],
        "price": [15000, 28500, 22000, 18000, 35000],
        "km":    [80000, 35000, 95000, 60000, 110000],
        "fuel":  ["Diesel", "Essence", "Diesel", "Essence", "Diesel"],
        "scraped_at": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"],
    })

    # Modèle 1 — Features
    predictor = CarPricePredictor()
    predictor.train(sample)
    result = predictor.predict_range(2020, 60000, "Toyota", "Diesel")
    print(f"Prix estimé Toyota 2020 / 60k km : {result}")

    # Modèle 2 — Tendance
    trend = PriceTrendPredictor()
    trend.train(sample)
    print(trend.get_full_history_with_prediction(7))
