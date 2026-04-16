"""
model_manager.py — Handles ML model persistence and versioning
"""
import os
from datetime import datetime
from predictor import CarPricePredictor

MODEL_DIR = "models"
os.makedirs(MODEL_DIR, exist_ok=True)

class ModelManager:
    def __init__(self):
        self.price_model_path = os.path.join(MODEL_DIR, "price_predictor.pkl")
        self.trend_model_path = os.path.join(MODEL_DIR, "trend_predictor.pkl")

    def load_or_train_price_model(self, df, force_retrain: bool = False):
        predictor = CarPricePredictor()

        if not force_retrain and os.path.exists(self.price_model_path):
            try:
                if predictor.load(self.price_model_path):
                    current_hash = predictor.get_data_hash(df) if hasattr(predictor, 'get_data_hash') else None
                    if getattr(predictor, '_last_data_hash', None) == current_hash:
                        print("✅ Loaded cached model (matches current data)")
                        return predictor, False
                    else:
                        print("🔄 Data changed, retraining...")
            except Exception as e:
                print(f"⚠️  Load failed ({e}), training fresh...")

        # Train new model
        print("🧠 Training new price model...")
        predictor.train(df)
        predictor.save(self.price_model_path)
        return predictor, True

    def get_model_age(self):
        if os.path.exists(self.price_model_path):
            mtime = os.path.getmtime(self.price_model_path)
            age_hours = (datetime.now().timestamp() - mtime) / 3600
            return age_hours
        return float('inf')


_manager = None

def get_manager():
    global _manager
    if _manager is None:
        _manager = ModelManager()
    return _manager
