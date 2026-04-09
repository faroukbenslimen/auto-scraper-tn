import streamlit as st
import pandas as pd
from analyzer import full_summary

def render_home_page(df):
    if df.empty:
        st.info("👈 Click on **Start Scraping** in the sidebar to collect data.")
        st.stop()

    summary = full_summary(df)
    
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
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{summary.get('total_listings', 0)}</div>
            <div class="metric-label">Live Listings</div></div>""", unsafe_allow_html=True)
    with col2:
        val = f"{int(ps.get('median', 0)):,} DT" if ps else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Market Value (Median)</div></div>""", unsafe_allow_html=True)
    with col3:
        val = f"{int(ps.get('min', 0)):,} DT" if ps else "—"
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
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{summary.get('unique_brands', 0)}</div>
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
    
    # ── Quick Tips / AI Insight ──────────────────────────────────────────────────
    st.subheader("💡 Market Context")
    c1, c2 = st.columns(2)
    with c1:
        st.info(f"**Insight**: The {top_brand} remains the most listed brand in this snapshot. If you're looking for liquidity, it's a safe bet.")
    with c2:
        if ps and ps.get('median', 0) > 0:
            st.success(f"**Pricing**: Half of the vehicles listed are under **{int(ps.get('median', 0)):,} DT**. Great opportunities for budget buyers!")

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("🏁 Market Extremes")
    
    from ui_utils import render_styled_table
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
