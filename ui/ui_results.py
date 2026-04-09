import streamlit as st
import pandas as pd
import os
from .ui_utils import render_styled_table

def render_results_page(df):
    st.title("📊 Market Listings Explorer")

    if df.empty:
        st.info("👈 Run scraping first.")
        st.stop()

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🎛️ Search & Precision Filters", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            brands = ["All"] + sorted(df["brand"].dropna().unique().tolist())
            selected_brand = st.selectbox("Brand", brands)

        with col2:
            fuels = ["All"] + sorted(df["fuel"].dropna().unique().tolist())
            selected_fuel = st.selectbox("Fuel", fuels)

        with col3:
            locations = ["All"] + sorted(df["location"].dropna().unique().tolist())
            selected_loc = st.selectbox("City", locations)

        col4, col5 = st.columns(2)
        prices = df["price"].dropna()
        price_min, price_max = int(prices.min()) if not prices.empty else 0, int(prices.max()) if not prices.empty else 100000
        with col4:
            price_range = st.slider("Price Range (DT)", price_min, price_max, (price_min, price_max), step=500)

        years = df["year"].dropna()
        year_min, year_max = int(years.min()) if not years.empty else 2000, int(years.max()) if not years.empty else 2025
        with col5:
            year_range = st.slider("Manufacturing Year", year_min, year_max, (year_min, year_max))

    # ── 3. Price History Analytics (Power-User Feature) ──────────────────────
    import sqlite3
    db_path = "data/cars.db"
    price_info = {}
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        # Select first and last price for each link to find drops
        query = """
            SELECT link, 
                   MAX(price) as max_price, 
                   MIN(price) as min_price, 
                   COUNT(price) as p_count 
            FROM price_history 
            GROUP BY link
        """
        history_df = pd.read_sql(query, conn)
        conn.close()
        
        # Create a lookup for drops
        for _, row in history_df.iterrows():
            if row['p_count'] > 1 and row['min_price'] < row['max_price']:
                price_info[row['link']] = {
                    "saved": int(row['max_price'] - row['min_price']),
                    "is_drop": True
                }

    # ── Apply filters ───────────────────────────────────────────────────────
    filtered = df.copy()
    if selected_brand != "All":
        filtered = filtered[filtered["brand"] == selected_brand]
    if selected_fuel != "All":
        filtered = filtered[filtered["fuel"] == selected_fuel]
    if selected_loc != "All":
        filtered = filtered[filtered["location"] == selected_loc]
    filtered = filtered[
        (filtered["price"].isna() | filtered["price"].between(price_range[0], price_range[1])) &
        (filtered["year"].isna() | filtered["year"].between(year_range[0], year_range[1]))
    ]

    # Add Market Info Column
    def get_market_badge(row):
        info = price_info.get(row["link"])
        if info:
            return f"📉 Price Drop!\n(-{info['saved']:,} DT)"
        
        # Check against today's date
        is_today = str(row["scraped_at"])[:10] == pd.Timestamp.today().strftime("%Y-%m-%d")
        if is_today:
            return "✨ New Listing"
            
        return "🔹 Stable"

    filtered["Market Status"] = filtered.apply(get_market_badge, axis=1)

    st.markdown(f"Found **{len(filtered)}** listing(s) matching your criteria.")

    # ── Export CSV ────────────────────────────────────────────────────────────
    csv = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 Download Export (.csv)", csv, "car_listings.csv", "text/csv")

    # ── Table ───────────────────────────────────────────────────────────────
    display_cols = ["image_url", "title", "brand", "year", "price", "Market Status", "km", "fuel", "location"]
    
    render_styled_table(filtered[display_cols].reset_index(drop=True), paginate=True, page_size=15, table_id="main_results")
