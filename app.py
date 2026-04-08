"""
app.py — Main Entry Point for the Auto Scraper Tunisie Dashboard
Modularized Architecture (Phase 4)
"""

import streamlit as st
import pandas as pd
import os
import time

# 1. Imports from our modular UI system
from ui_utils import detect_dark_mode, setup_plotly_theme, apply_custom_css
from ui_home import render_home_page
from ui_results import render_results_page
from ui_visuals import render_visuals_page
from ui_ai import render_ai_page

# 2. Project Engine Imports
from scraper import scrape_cars, save_data, load_data
from cleaner import clean_dataframe

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

# ─── Data State Management ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def get_cached_data():
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
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Flag_of_Tunisia.svg/32px-Flag_of_Tunisia.svg.png", width=30)
    st.title("🚗 Auto Scraper TN")
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
        with st.spinner("Extracting market data..."):
            try:
                raw = scrape_cars(num_pages=pages_to_scrape)
                if not raw.empty:
                    save_data(raw)
                    refresh_app_data()
                    st.success(f"Successfully scraped {len(raw)} listings!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("No listings found.")
            except Exception as e:
                st.error(f"Scraper Error: {e}")

    if st.button("🗑️ Wipe All Database"):
        for f_path in ["data/cars.db", "data/cars.csv"]:
            if os.path.exists(f_path):
                os.remove(f_path)
        refresh_app_data()
        st.info("Market data wiped clean.")
        time.sleep(1)
        st.rerun()

    st.markdown("---")
    st.caption("Auto Market Intelligence v2.0\nSource: automobile.tn")

# ─── Main Page Routing ───────────────────────────────────────────────────────
df = get_cached_data()

# 🛡️ 3. Private Power-User: Startup Auto-Sync
if "startup_sync_done" not in st.session_state:
    st.session_state.startup_sync_done = False

if not st.session_state.startup_sync_done:
    st.toast("🔄 Proactive Market Sync: Checking for new listings...", icon="🔍")
    try:
        # Perform a quick 5-page background sync on launch
        new_raw = scrape_cars(num_pages=5)
        if not new_raw.empty:
            save_data(new_raw)
            refresh_app_data()
            st.toast("✅ Market data updated!", icon="✨")
    except Exception as e:
        st.toast(f"⚠️ Startup Sync failed: {e}")
    st.session_state.startup_sync_done = True
    st.rerun()

if page == "🏠 Home":
    render_home_page(df)
elif page == "📊 Results & Filters":
    render_results_page(df)
elif page == "📈 Visualizations":
    render_visuals_page(df)
elif page == "🤖 AI Prediction":
    render_ai_page(df)
