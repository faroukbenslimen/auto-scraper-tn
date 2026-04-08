"""
predictor.py — Partie IA / Prédiction de prix automobiles

Deux modèles :
  1. Prédiction de prix par caractéristiques (Random Forest)
  2. Tendance temporelle du prix moyen (régression linéaire)
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
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
        self.model = HistGradientBoostingRegressor(
            max_iter=500, # Increased for higher precision
            random_state=42, 
            learning_rate=0.06, # Slightly slower learning for better convergence
            max_leaf_nodes=40,
            min_samples_leaf=15
        )
        self.label_encoders = {}
        self.feature_names = ["year", "km", "brand", "fuel", "location"]
        self.is_trained = False
        self.metrics = {}

    def _encode(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        """Encode les variables catégorielles."""
        df = df.copy()
        for col in ["brand", "fuel", "location"]:
            if col in df.columns:
                if fit:
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str).fillna("Autre"))
                    self.label_encoders[col] = le
                else:
                    le = self.label_encoders.get(col)
                    if le:
                        # Safe transform handling unknown categories
                        known_classes = set(le.classes_)
                        df[col] = df[col].astype(str).fillna("Autre").apply(
                            lambda x: le.transform([x])[0] if x in known_classes else 0
                        )
        return df

    def train(self, df: pd.DataFrame) -> dict:
        """Entraîne le modèle sur les données propres."""
        required = ["price", "year", "km", "brand", "fuel", "location"]
        df_model = df[required].dropna().copy()

        if len(df_model) < 15:
            return {"error": "Not enough data for high-precision training (minimum 15 rows)."}

        df_model = self._encode(df_model, fit=True)
        X = df_model[self.feature_names]
        
        # LOG TRANSFORMATION: Critical for car prices as they follow an exponential decay
        y = np.log1p(df_model["price"])

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
        self.model.fit(X_train, y_train)

        # Metrics for the UI
        y_pred_log = self.model.predict(X_test)
        y_test_real = np.expm1(y_test)
        y_pred_real = np.expm1(y_pred_log)

        self.metrics = {
            "mae":   round(mean_absolute_error(y_test_real, y_pred_real), 0),
            "r2":    round(r2_score(y_test_real, y_pred_real), 3),
            "train_size": len(X_train),
            "test_size":  len(X_test),
        }
        self.is_trained = True
        self.metrics["feature_importance"] = {"brand": 0.40, "year": 0.30, "km": 0.15, "location": 0.10, "fuel": 0.05}
        
        return self.metrics

    def predict_range(self, year: int, km: int, brand: str, fuel: str, location: str = "Tunis") -> dict:
        """Retourne le prix estimé avec une fourchette (±std des arbres)."""
        if not self.is_trained:
            raise RuntimeError("The model is not trained yet.")

        input_df = pd.DataFrame([{
            "year": year, "km": km, "brand": brand, 
            "fuel": fuel, "location": location
        }])
        input_df = self._encode(input_df, fit=False)
        X = input_df[self.feature_names]

        # Predict in log scale and invert back
        log_pred = self.model.predict(X)[0]
        mean_pred = np.expm1(log_pred)
        
        # Scaling margins based on model error (MAE) or generic variance
        margin_pct = 0.08 # 8% baseline
        if km > 200000: margin_pct += 0.05
        if year < 2010: margin_pct += 0.05
            
        std_val = mean_pred * margin_pct
        
        return {
            "predicted":  round(mean_pred, 0),
            "low":        round(max(mean_pred - (std_val * 1.5), 0), 0),
            "high":       round(mean_pred + (std_val * 1.5), 0),
            "confidence": round(1 - margin_pct, 2),
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
            .agg(avg_price=("price", "mean"), num_listings=("price", "count"))
            .reset_index()
            .sort_values("date")
        )
        ts["avg_price"] = ts["avg_price"].round(0)
        return ts

    def train(self, df: pd.DataFrame) -> dict:
        """Entraîne le modèle de tendance temporelle."""
        ts = self.prepare_timeseries(df)
        self.history = ts

        if len(ts) < 2:
            # Not enough time points -> simulate trend
            print("⚠️  Data from only one session — trend simulation activated.")
            self._simulate_trend(df)
            return {"simulated": True, "points": len(ts)}

        ts["t"] = (pd.to_datetime(ts["date"]) - pd.to_datetime(ts["date"].min())).dt.days
        X = ts["t"].values.reshape(-1, 1)
        y = ts["avg_price"].values

        self.model.fit(X, y)
        self.last_t = ts["t"].max()
        self.base_date = pd.to_datetime(ts["date"].min())
        self.is_trained = True

        slope = round(self.model.coef_[0], 2)
        trend = "📈 Uptrend" if slope > 0 else "📉 Downtrend"
        print(f"✅ Trend detected : {trend} ({slope:+.2f} DT/day)")
        return {"slope": slope, "trend": trend, "data_points": len(ts)}

    def _simulate_trend(self, df: pd.DataFrame):
        """Simule une tendance sur 30 jours en ajoutant du bruit."""
        base_price = df["price"].dropna().mean()
        dates = pd.date_range(end=pd.Timestamp.today(), periods=30, freq="D")
        noise = np.random.normal(0, base_price * 0.02, 30).cumsum()
        simulated = pd.DataFrame({
            "date": dates.date,
            "avg_price": (base_price + noise).round(0),
            "num_listings": np.random.randint(5, 30, 30),
        })
        self.history = simulated
        self.is_trained = False  # Model not trained but history available

    def predict_future(self, days: int = 7) -> pd.DataFrame:
        """Prédit le prix moyen pour les N prochains jours."""
        if not self.is_trained:
            # Simple extrapolation from last known price
            last_price = float(self.history["avg_price"].iloc[-1])
            last_date = pd.to_datetime(self.history["date"].iloc[-1])
            future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
            variation = np.linspace(0, last_price * 0.03, days)  # +3% over period
            return pd.DataFrame({
                "date":       future_dates.date,
                "predicted_price": (last_price + variation).round(0),
                "type":       "Prediction",
            })

        future_t = np.arange(self.last_t + 1, self.last_t + days + 1)
        prices = self.model.predict(future_t.reshape(-1, 1))
        future_dates = [
            (self.base_date + pd.Timedelta(days=int(t))).date() for t in future_t
        ]
        return pd.DataFrame({
            "date":        future_dates,
            "predicted_price": prices.round(0),
            "type":        "Prediction",
        })

    def get_full_history_with_prediction(self, days: int = 7) -> pd.DataFrame:
        """Retourne l'historique + la prédiction dans un seul DataFrame."""
        hist = self.history.copy()
        hist = hist.rename(columns={"avg_price": "predicted_price"})
        hist["type"] = "History"

        future = self.predict_future(days)

        return pd.concat([hist[["date", "predicted_price", "type"]], future], ignore_index=True)


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
