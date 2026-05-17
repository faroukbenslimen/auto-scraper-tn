"""
diagnostic.py — Full system diagnostic for Auto Scraper Tunisie
Run: python diagnostic.py
"""
import sys, traceback, time, os

print("=== AUTO SCRAPER TN — FULL DIAGNOSTIC ===")
print(f"Python: {sys.version}")
print()

errors = []
warnings = []
perf = {}

# ─── 1. Core imports ──────────────────────────────────────────────────────────
print("[1/8] Core imports...")
for pkg in ["streamlit", "pandas", "sklearn", "plotly", "httpx", "lxml", "bs4", "requests", "numpy"]:
    try:
        t0 = time.time()
        mod = __import__(pkg)
        ver = getattr(mod, "__version__", "?")
        elapsed = time.time() - t0
        perf[f"import_{pkg}"] = elapsed
        flag = "  ⚠️  SLOW" if elapsed > 1.5 else ""
        print(f"  ✅ {pkg} {ver} ({elapsed:.2f}s){flag}")
    except Exception as e:
        errors.append(f"import {pkg}: {e}")
        print(f"  ❌ {pkg}: {e}")

# ─── 2. Project module imports ────────────────────────────────────────────────
print()
print("[2/8] Project module imports...")
modules = ["scraper", "cleaner", "analyzer", "predictor", "chat_helper"]
for mod_name in modules:
    try:
        t0 = time.time()
        mod = __import__(mod_name)
        elapsed = time.time() - t0
        perf[f"import_{mod_name}"] = elapsed
        flag = "  ⚠️  SLOW" if elapsed > 1.0 else ""
        print(f"  ✅ {mod_name} ({elapsed:.2f}s){flag}")
    except Exception as e:
        errors.append(f"import {mod_name}: {e}")
        print(f"  ❌ {mod_name}: {e}")
        traceback.print_exc()

# ─── 3. Data pipeline ─────────────────────────────────────────────────────────
print()
print("[3/8] Data pipeline...")
df = None
from scraper import load_data
from cleaner import clean_dataframe

if os.path.exists("data/cars.db"):
    t0 = time.time()
    raw = load_data()
    perf["load_data"] = time.time() - t0
    print(f"  load_data: {len(raw)} rows in {perf['load_data']:.2f}s")

    t0 = time.time()
    df = clean_dataframe(raw)
    perf["clean_dataframe"] = time.time() - t0
    print(f"  clean_dataframe: {len(df)} rows in {perf['clean_dataframe']:.2f}s")
    print(f"  Columns: {list(df.columns)}")
    nan_prices = df["price"].isna().sum()
    print(f"  NaN prices: {nan_prices} / {len(df)} ({nan_prices/len(df)*100:.1f}%)")
    if nan_prices / len(df) > 0.3:
        warnings.append(f"High NaN price rate: {nan_prices/len(df)*100:.0f}% — scraper may be extracting malformed data")
    print(f"  Price range: {df['price'].min():.0f} - {df['price'].max():.0f} DT")
    print(f"  Unique brands: {df['brand'].nunique()}")
    print(f"  Year range: {df['year'].min():.0f} - {df['year'].max():.0f}")
else:
    warnings.append("No data/cars.db — run the scraper first")
    print("  ⚠️  No database found. Skipping data tests.")

# ─── 4. Analyzer ──────────────────────────────────────────────────────────────
print()
print("[4/8] Analyzer...")
if df is not None:
    from analyzer import full_summary, find_market_bargains, by_brand, by_fuel, by_location, by_year
    t0 = time.time()
    try:
        summary = full_summary(df)
        perf["full_summary"] = time.time() - t0
        flag = "  ⚠️  SLOW" if perf["full_summary"] > 2.0 else ""
        print(f"  full_summary OK in {perf['full_summary']:.2f}s{flag} — {summary['total_listings']} listings")
    except Exception as e:
        errors.append(f"full_summary: {e}")
        traceback.print_exc()

    for fn_name, fn in [("by_brand", by_brand), ("by_fuel", by_fuel), ("by_location", by_location), ("by_year", by_year)]:
        t0 = time.time()
        try:
            result = fn(df)
            elapsed = time.time() - t0
            print(f"  {fn_name} OK ({elapsed:.3f}s, {len(result)} rows)")
        except Exception as e:
            errors.append(f"{fn_name}: {e}")
else:
    print("  ⏭️  Skipped (no data)")

# ─── 5. ML Predictor ──────────────────────────────────────────────────────────
print()
print("[5/8] ML Predictor training...")
if df is not None:
    from predictor import CarPricePredictor, PriceTrendPredictor
    
    t0 = time.time()
    try:
        p = CarPricePredictor()
        metrics = p.train(df)
        perf["predictor_train"] = time.time() - t0
        flag = "  ⚠️  SLOW — consider reducing max_iter" if perf["predictor_train"] > 3.0 else ""
        print(f"  CarPricePredictor train in {perf['predictor_train']:.2f}s{flag}")
        print(f"  Metrics: MAE={metrics.get('mae','?'):.0f} DT, R2={metrics.get('r2','?'):.3f}, samples={metrics.get('train_size','?')}")
        if metrics.get("r2", 0) < 0.5:
            warnings.append(f"Low R2 score ({metrics.get('r2',0):.3f}) — model accuracy poor, may need more data")
        
        t0 = time.time()
        r = p.predict_range(2019, 80000, "Toyota", "Diesel", "Tunis")
        print(f"  predict_range OK ({time.time()-t0:.3f}s): {r}")
    except Exception as e:
        errors.append(f"CarPricePredictor: {e}")
        traceback.print_exc()

    t0 = time.time()
    try:
        trend = PriceTrendPredictor()
        trend.train(df)
        perf["trend_train"] = time.time() - t0
        print(f"  PriceTrendPredictor train in {perf['trend_train']:.2f}s")
        future = trend.predict_future(7)
        print(f"  predict_future(7) OK: {len(future)} days predicted")
    except Exception as e:
        errors.append(f"PriceTrendPredictor: {e}")
        traceback.print_exc()
else:
    print("  ⏭️  Skipped (no data)")

# ─── 6. Bargain detection ─────────────────────────────────────────────────────
print()
print("[6/8] Bargain detection...")
if df is not None:
    t0 = time.time()
    try:
        p2 = CarPricePredictor()
        p2.train(df)
        bargains = find_market_bargains(df, p2, threshold=0.15)
        perf["bargain_detection"] = time.time() - t0
        print(f"  find_market_bargains OK in {perf['bargain_detection']:.2f}s — {len(bargains)} bargains found")
        if len(bargains) > 0:
            print(f"  Top bargain: {bargains.iloc[0]['title']} — {bargains.iloc[0]['savings_pct']*100:.0f}% below market")
    except Exception as e:
        errors.append(f"bargain detection: {e}")
        traceback.print_exc()
else:
    print("  ⏭️  Skipped (no data)")

# ─── 7. Chat helper ───────────────────────────────────────────────────────────
print()
print("[7/8] Chat helper...")
try:
    from chat_helper import extract_intent_and_entities
    tests = [
        ("cheapest Toyota diesel 2019", "min_price"),
        ("estimate Peugeot 208 2020 50000km", "predict"),
        ("how many cars in Sousse", "count"),
        ("average price bmw 2018", "avg_price"),
    ]
    for query, expected_intent in tests:
        try:
            intent, entities = extract_intent_and_entities(
                query, ["Toyota","Peugeot","BMW"], ["Diesel","Gasoline"], ["Tunis","Sfax","Sousse"], []
            )
            ok = "✅" if intent == expected_intent else "⚠️ "
            print(f"  {ok} {repr(query)}: intent={intent} (expected {expected_intent}), entities={entities}")
            if intent != expected_intent:
                warnings.append(f"Chat intent mismatch for '{query}': got '{intent}', expected '{expected_intent}'")
        except Exception as e:
            errors.append(f"chat query '{query}': {e}")
except Exception as e:
    errors.append(f"chat_helper import: {e}")
    traceback.print_exc()

# ─── 8. Database integrity ────────────────────────────────────────────────────
print()
print("[8/8] Database integrity...")
if os.path.exists("data/cars.db"):
    import sqlite3
    conn = sqlite3.connect("data/cars.db")
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    print(f"  Tables: {[t[0] for t in tables]}")
    for t in tables:
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        print(f"  {t[0]}: {cnt} rows")
    
    if "price_history" not in [t[0] for t in tables]:
        warnings.append("price_history table missing — price drop tracking unavailable")
    conn.close()
else:
    print("  ⚠️  No database found")

# ─── Summary ──────────────────────────────────────────────────────────────────
print()
print("=" * 55)
print("PERFORMANCE SUMMARY:")
for k, v in sorted(perf.items(), key=lambda x: -x[1]):
    bar = "█" * int(v * 5)
    flag = " ← SLOW" if v > 2.0 else ""
    print(f"  {k:<30} {v:6.2f}s  {bar}{flag}")

print()
total_startup = sum(v for k,v in perf.items() if "import" in k or k in ["load_data","clean_dataframe"])
print(f"  Estimated cold startup time:  {total_startup:.1f}s")

print()
print(f"ERRORS ({len(errors)}):")
for e in errors:
    print(f"  ❌ {e}")

print()
print(f"WARNINGS ({len(warnings)}):")
for w in warnings:
    print(f"  ⚠️  {w}")

if not errors:
    print()
    print("✅ All systems operational!")
else:
    print()
    print("❌ Fix the errors above before running the app.")
