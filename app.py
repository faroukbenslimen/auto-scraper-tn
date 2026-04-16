"""
app.py — Main Entry Point for the Auto Scraper Tunisie Dashboard
Modularized Architecture (Phase 4)
"""

import streamlit as st
import os
import time
import threading
from datetime import datetime
import json
import socketserver
from http.server import BaseHTTPRequestHandler

# Lightweight UI utilities (no heavy deps)
from ui.ui_utils import detect_dark_mode, setup_plotly_theme, apply_custom_css

# Heavy UI page modules and engine are imported lazily (inside functions)
# to avoid blocking Streamlit's initial render with sklearn/httpx/lxml import costs.

# ─── Initialization & Theme ───────────────────────────────────────────────────
is_dark = detect_dark_mode()
setup_plotly_theme(is_dark)

st.set_page_config(
    page_title="🚗 Auto Scraper Tunisie",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css(is_dark)


# ─── Lightweight health endpoint (127.0.0.1:8765) ─────────────────────────
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/healthz":
            self.send_response(404)
            self.end_headers()
            return
        status = {"ok": True}
        status["model_exists"] = os.path.exists("models/price_predictor.pkl")
        status["data_exists"] = os.path.exists("data/cars.db") or os.path.exists("data/cars.csv")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status).encode())


def _start_health_server(port: int = 8765):
    try:
        server = socketserver.TCPServer(("127.0.0.1", port), _HealthHandler)
        server.serve_forever()
    except Exception as e:
        print(f"Health server failed: {e}")


# Start the health server in background (daemon)
try:
    t_h = threading.Thread(target=_start_health_server, args=(8765,), daemon=True)
    t_h.start()
except Exception:
    pass

# ─── Data State Management ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_cached_data():
    # Lazy imports: these are only executed after the UI is already rendered
    import pandas as pd
    from scraper import load_data
    from cleaner import clean_dataframe
    raw = load_data()
    return clean_dataframe(raw) if not raw.empty else pd.DataFrame()

def refresh_app_data():
    st.cache_data.clear()

def handle_theme_toggle():
    config_path = os.path.join(".streamlit", "config.toml")
    if not os.path.exists(config_path): return
    
    with open(config_path, "r") as f:
        text = f.read()
    
    if 'base="dark"' in text:
        text = text.replace('base="dark"', 'base="light"')
        text = text.replace('backgroundColor="#0a0a0f"', 'backgroundColor="#ffffff"')
        text = text.replace('secondaryBackgroundColor="#14141f"', 'secondaryBackgroundColor="#f0f2f6"')
        text = text.replace('textColor="#ffffff"', 'textColor="#31333F"')
    else:
        text = text.replace('base="light"', 'base="dark"')
        text = text.replace('backgroundColor="#ffffff"', 'backgroundColor="#0a0a0f"')
        text = text.replace('secondaryBackgroundColor="#f0f2f6"', 'secondaryBackgroundColor="#14141f"')
        text = text.replace('textColor="#31333F"', 'textColor="#ffffff"')
        
    with open(config_path, "w") as f:
        f.write(text)
    
    time.sleep(0.3)
    st.rerun()

# ─── Sidebar Navigation & State Sync ──────────────────────────────────────────
# 1. Initialize session state if missing
if "current_page" not in st.session_state:
    # Use URL param as initial source of truth
    url_page = st.query_params.get("page", "🏠 Home")
    st.session_state.current_page = url_page

def on_nav_change():
    """Callback to sync session state with URL when radio changes."""
    st.session_state.current_page = st.session_state.nav_radio
    st.query_params["page"] = st.session_state.nav_radio

with st.sidebar:
    # Use a more reliable flag source or an emoji to avoid broken icons
    st.markdown("### 🇹🇳 Auto Scraper TN")
    st.markdown("---")
    
    nav_options = {
        "🏠 Home": 0,
        "📊 Results & Filters": 1,
        "📈 Visualizations": 2,
        "🤖 AI Prediction": 3
    }
    
    # Get index for radio based on current state
    start_index = nav_options.get(st.session_state.current_page, 0)
    
    page = st.radio(
        "Navigation", 
        list(nav_options.keys()), 
        index=start_index,
        key="nav_radio",
        on_change=on_nav_change
    )
    
    # Final confirmation of current page
    page = st.session_state.current_page
    
    st.markdown("---")
    if st.button("🌓 Toggle Theme"):
        handle_theme_toggle()

    st.markdown("---")
    st.subheader("⚙️ Scraping Engine")
    pages_to_scrape = st.slider("Depth (Pages)", 1, 150, 5)

    if st.button("🚀 Run Scraper Now"):
        _scrape_start = time.time()
        with st.spinner("Extracting market data..."):
            try:
                from scraper import scrape_cars, save_data
                raw = scrape_cars(num_pages=pages_to_scrape)
                _elapsed = time.time() - _scrape_start
                _mins, _secs = divmod(int(_elapsed), 60)
                _time_str = f"{_mins}m {_secs}s" if _mins else f"{_secs:.0f}s"
                _rate = f"{len(raw) / _elapsed:.1f}" if _elapsed > 0 and not raw.empty else "0"

                if not raw.empty:
                    save_data(raw)
                    refresh_app_data()
                    st.success(
                        f"✅ Done in **{_time_str}** — "
                        f"**{len(raw)}** listings scraped "
                        f"({_rate} listings/sec, {pages_to_scrape} pages)"
                    )
                    time.sleep(2)
                    st.rerun()
                else:
                    st.warning(f"No listings found. (took {_time_str})")
            except Exception as e:
                _elapsed = time.time() - _scrape_start
                st.error(f"Scraper Error after {_elapsed:.1f}s: {e}")

    if st.button("🗑️ Wipe All Database"):
        for f_path in ["data/cars.db", "data/cars.csv"]:
            if os.path.exists(f_path):
                os.remove(f_path)
        refresh_app_data()
        st.info("Market data wiped clean.")
        time.sleep(1)
        st.rerun()

    st.markdown("---")
    # Show last sync info (lazy import - scraper already imported if button clicked)
    from scraper import get_last_sync_time
    sync_status = get_last_sync_time()
    ls = sync_status["last_sync"]
    ls_str = ls.strftime("%Y-%m-%d %H:%M") if ls != datetime.min else "Never"
    st.caption(f"🕒 Last Full Sync: {ls_str}")
    if sync_status["is_syncing"]:
        st.caption("🔄 **Sync in progress...**")
    st.caption("Auto Market Intelligence v2.3 (Hardened)\nSource: automobile.tn")

# ─── Main Page Routing ───────────────────────────────────────────────────────
# Load data — @st.cache_data ensures this is fast on subsequent runs
df = get_cached_data()

# Bootstrap models on startup (load cached model if compatible)
def bootstrap_models(df):
    from model_manager import get_manager
    if df is None or df.empty:
        return None
    mgr = get_manager()
    predictor, was_trained = mgr.load_or_train_price_model(df)
    if was_trained:
        try:
            st.toast("🧠 New AI model trained and cached!")
        except Exception:
            pass
    return predictor

if "predictor_bootstrapped" not in st.session_state:
    try:
        bootstrap_models(df)
    except Exception:
        pass
    st.session_state.predictor_bootstrapped = True

# 🛡️ Background Auto-Sync (6-Hour Rule)
def background_sync_task():
    """Background task to scrape 150 pages and update the model."""
    from scraper import scrape_cars, save_data, set_sync_lock
    try:
        set_sync_lock(True)
        new_raw = scrape_cars(num_pages=150)
        if not new_raw.empty:
            save_data(new_raw)
            st.cache_data.clear()
            st.session_state.sync_finished_at = datetime.now().strftime("%H:%M")
        else:
            set_sync_lock(False)
    except Exception as e:
        from scraper import set_sync_lock as _sl
        print(f"Background Sync Failed: {e}")
        _sl(False)

from scraper import get_last_sync_time as _get_sync
sync_status = _get_sync()
last_sync = sync_status["last_sync"]
is_syncing_globally = sync_status["is_syncing"]
hours_since = (datetime.now() - last_sync).total_seconds() / 3600

if "sync_thread_started" not in st.session_state:
    st.session_state.sync_thread_started = False

# Only start if data is old AND no one else is currently syncing
if hours_since >= 6 and not st.session_state.sync_thread_started and not is_syncing_globally:
    st.toast("🌍 Deep Market Crawl (150 Pages) started in background...", icon="🔍")
    thread = threading.Thread(target=background_sync_task, daemon=True)
    thread.start()
    st.session_state.sync_thread_started = True

# Notify if sync just finished
if "sync_finished_at" in st.session_state:
    st.toast(f"✅ Market intelligence updated at {st.session_state.sync_finished_at}!", icon="✨")
    del st.session_state.sync_finished_at

# Lazy-import page renderers only when the page is actually navigated to
if page == "🏠 Home":
    from ui.ui_home import render_home_page
    render_home_page(df)
elif page == "📊 Results & Filters":
    from ui.ui_results import render_results_page
    render_results_page(df)
elif page == "📈 Visualizations":
    from ui.ui_visuals import render_visuals_page
    render_visuals_page(df)
elif page == "🤖 AI Prediction":
    from ui.ui_ai import render_ai_page
    render_ai_page(df)
