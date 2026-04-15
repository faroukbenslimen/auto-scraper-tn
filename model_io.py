"""model_io.py

Safe model persistence helpers.

This module wraps `joblib` save/load with conservative error handling
and optional SHA256 verification. It avoids crashing the app when a
model file is corrupted or incompatible.

Usage:
    from model_io import save_model, load_model
    save_model(obj, "models/price_predictor.pkl")
    model = load_model("models/price_predictor.pkl")

Note: Loading pickles can execute code. Only load model files you
created in this project and consider storing/checking a checksum.
"""
import os
import hashlib
import joblib
from typing import Any, Optional, Tuple


def _sha256_of_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def save_model(obj: Any, path: str) -> Optional[str]:
    """Safely save a model object to `path` and return its SHA256 hex.

    Returns the hex digest on success, or None on failure.
    """
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(obj, path)
        digest = _sha256_of_file(path)
        return digest
    except Exception as e:
        print(f"[model_io] Failed to save model to {path}: {e}")
        return None


def load_model(path: str, expected_hash: Optional[str] = None) -> Optional[Any]:
    """Safely load a model from `path`.

    If `expected_hash` is provided, the file's SHA256 must match or None is returned.
    Returns the loaded object, or None on error / mismatch.
    """
    if not os.path.exists(path):
        print(f"[model_io] Model file not found: {path}")
        return None
    try:
        if expected_hash is not None:
            actual = _sha256_of_file(path)
            if actual != expected_hash:
                print(f"[model_io] Hash mismatch for {path}: expected {expected_hash[:8]}.. got {actual[:8]}..")
                return None

        obj = joblib.load(path)
        return obj
    except Exception as e:
        print(f"[model_io] Failed to load model from {path}: {e}")
        return None


def get_model_hash(path: str) -> Optional[str]:
    """Return SHA256 digest for model file or None if not available."""
    if not os.path.exists(path):
        return None
    try:
        return _sha256_of_file(path)
    except Exception:
        return None
