import streamlit as st
import pandas as pd
import numpy as np
import hashlib
from .ui_utils import render_styled_table

# ── Cached heavy computations ─────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _cached_summary(df):
    from analyzer import full_summary
    return full_summary(df)

def _get_data_hash(df):
    if df is None or df.empty:
        return "empty"
    brand_counts = df['brand'].value_counts().to_json()
    return hashlib.md5(f"{brand_counts}:{len(df)}:{int(df['price'].sum() if 'price' in df.columns and not df['price'].isna().all() else 0)}".encode()).hexdigest()[:16]


@st.cache_resource
def _cached_predictor(_df_hash, _df):
    from predictor import CarPricePredictor
    p = CarPricePredictor()

    # Try to load saved model first
    try:
        if p.load():
            current_hash = p.get_data_hash(_df) if hasattr(p, 'get_data_hash') else _df_hash
            if getattr(p, '_last_data_hash', None) == current_hash:
                print(f"  [Cache] Using loaded model (hash: {current_hash})")
                return p
            print(f"  [Cache] Data changed ({getattr(p, '_last_data_hash', 'none')} -> {current_hash}), retraining...")
    except Exception:
        pass

    p.train(_df)
    return p

@st.cache_data(show_spinner=False)
def _cached_bargains(df):
    """Runs bulk bargain detection — returns only the bargains DataFrame (serializable)."""
    from analyzer import find_market_bargains
    df_hash = _get_data_hash(df)
    predictor = _cached_predictor(df_hash, df)
    if predictor.is_trained:
        return find_market_bargains(df, predictor, threshold=0.15)
    return pd.DataFrame()

def render_home_page(df):
    if df.empty:
        st.info("👈 Click on **Start Scraping** in the sidebar to collect data.")
        st.stop()

    with st.spinner("Loading market intelligence..."):
        summary = _cached_summary(df)

    st.title("🚀 Market Intelligence Dashboard")
    st.markdown("Real-time analysis of the Tunisian automotive market.")
    
    st.markdown("---")
    
    # ── KPI Dashboard ────────────────────────────────────────────────────────────
    st.subheader("📊 Market At a Glance")
    
    ps = summary.get("price_stats", {})
    ys = summary.get("year_stats", {})
    ks = summary.get("km_stats", {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        val = summary.get('total_listings', 0)
        val_str = f"{val}" if val > 0 else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val_str}</div>
            <div class="metric-label">Live Listings</div></div>""", unsafe_allow_html=True)
    with col2:
        val = f"{int(ps.get('median', 0)):,} DT" if ps and ps.get('median', 0) > 0 else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Market Value (Median)</div></div>""", unsafe_allow_html=True)
    with col3:
        val = f"{int(ps.get('min', 0)):,} DT" if ps and ps.get('min', 0) > 0 else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Best Entry Price</div></div>""", unsafe_allow_html=True)
    with col4:
        val = f"{int(ps.get('max', 0)):,} DT" if ps else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Premium Ceiling</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        val = summary.get('unique_brands', 0)
        val_str = f"{val}" if val > 0 else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val_str}</div>
            <div class="metric-label">Manufacturers</div></div>""", unsafe_allow_html=True)
    with col6:
        val = f"{int(ys.get('newest', 0))}" if ys else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Newest Model Year</div></div>""", unsafe_allow_html=True)
    with col7:
        val = f"{int(ks.get('median', 0)):,} km" if ks else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Avg. Wear (Median)</div></div>""", unsafe_allow_html=True)
    with col8:
        # Find the most frequent brand
        top_brand = df["brand"].mode().iloc[0] if not df["brand"].mode().empty else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value" style="font-size: 1.5rem; line-height: 2.2rem;">{top_brand}</div>
            <div class="metric-label">Market Leader</div></div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── 🔥 AI Market Bargains ──────────────────────────────────
    st.subheader("🔥 Top Market Bargains (AI Verified)")
    st.markdown("These listings are currently priced at least **15% below** our AI's estimated market value.")

    # Use cached bargain detection (only retrains when data changes)
    df_hash = _get_data_hash(df)
    predictor = _cached_predictor(df_hash, df)
    bargains = _cached_bargains(df)

    if predictor.is_trained:
        if not bargains.empty:
            display_bargains = bargains.head(5).copy()
            display_bargains["Saving"] = (display_bargains["savings_pct"] * 100).apply(lambda x: f"🔥 {x:.1f}% OFF")
            display_bargains["AI Fair Price"] = display_bargains["predicted_price"].apply(lambda x: f"{int(x):,} DT")
            display_bargains["Market Price"] = display_bargains["price"].apply(lambda x: f"{int(x):,} DT")
            cols_to_show = ["image_url", "title", "Market Price", "AI Fair Price", "Saving", "link"]
            render_styled_table(display_bargains[cols_to_show], table_id="market_bargains")
            st.success("💡 **Intelligence Tip**: The items above represent the highest statistical value in the dataset based on current trends.")
        else:
            st.info("No major bargains detected at a 15% threshold. Most listings are priced close to market value.")
    else:
        st.warning("AI model still maturing. Bargain detection will be available once more data is collected.")


    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏁 Market Extremes")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("💰 Most Expensive")
        render_styled_table(summary["top5_expensive"], table_id="top_expensive")
    with col_b:
        st.subheader("🤑 Cheapest")
        render_styled_table(summary["bottom5_cheapest"], table_id="top_cheapest")

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("✨ Newest")
        render_styled_table(summary["top5_newest"], table_id="top_newest")
    with col_d:
        st.subheader("📉 Lowest Mileage")
        render_styled_table(summary["top5_low_km"], table_id="top_low_km")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🔍 Getting Started")
    st.write("Use the sidebar to explore the market in depth, or head over to the **AI Assistant** tab to predict the price of a specific vehicle.")
