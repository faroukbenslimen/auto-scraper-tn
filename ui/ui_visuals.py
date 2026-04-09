import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from analyzer import by_brand, by_fuel, by_location, by_year

def render_visuals_page(df):
    st.title("📈 Market Visualizations")

    if df.empty:
        st.info("👈 Run scraping first.")
        st.stop()

    COLORS = ["#3b82f6", "#10b981", "#8b5cf6", "#f43f5e", "#f59e0b", "#06b6d4"]

    # ── 1. Distribution des prix ──────────────────────────────────────────────
    st.markdown('<div class="section-title">1. Price Distribution</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        prices_clean = df["price"].dropna()
        fig_hist = px.histogram(
            prices_clean, nbins=30,
            title="Price Histogram (DT)",
            labels={"value": "Price (DT)", "count": "Count"},
            color_discrete_sequence=["#00d4ff"],
        )
        fig_hist.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_box = px.box(
            df.dropna(subset=["price", "fuel"]),
            x="fuel", y="price", color="fuel",
            title="Price by Fuel Type",
            labels={"price": "Price (DT)", "fuel": "Fuel"},
            color_discrete_sequence=COLORS,
        )
        fig_box.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_box, use_container_width=True)

    # ── 2. Top 10 marques ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">2. Top 10 Brands Analysis</div>', unsafe_allow_html=True)
    brand_df = by_brand(df).head(10)

    col3, col4 = st.columns(2)
    with col3:
        fig_bar = px.bar(
            brand_df, x="brand", y="num_listings",
            title="Listings Volume by Brand",
            labels={"brand": "Brand", "num_listings": "Listings"},
        )
        fig_bar.update_traces(marker_color="#00d4ff", opacity=0.8)
        fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col4:
        fig_bar2 = px.bar(
            brand_df.dropna(subset=["avg_price"]),
            x="brand", y="avg_price",
            title="Avg price by Brand (DT)",
            labels={"brand": "Brand", "avg_price": "Avg Price (DT)"},
        )
        fig_bar2.update_traces(marker_color="#e94560", opacity=0.8)
        fig_bar2.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar2, use_container_width=True)

    # ── 3. Geographical & Fuel Breakdown ─────────────────────────────────────
    st.markdown('<div class="section-title">3. Market Composition</div>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)

    fuel_df = by_fuel(df)
    with col5:
        fig_pie = px.pie(
            fuel_df, names="fuel", values="num_listings",
            title="Fuel Type Breakdown",
            color_discrete_sequence=COLORS,
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col6:
        loc_df = by_location(df).head(10)
        fig_loc = px.bar(
            loc_df, x="num_listings", y="location", orientation="h",
            title="Listings for the Top 10 Cities",
            labels={"location": "City", "num_listings": "Listings"},
        )
        fig_loc.update_traces(marker_color="#b300ff", opacity=0.8)
        fig_loc.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_loc, use_container_width=True)

    # ── 4. Temporal Trends ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">4. Market Maturity: Price vs Age</div>', unsafe_allow_html=True)
    year_df = by_year(df)
    if not year_df.empty:
        fig_line = px.area(
            year_df, x="year", y="avg_price",
            title="Historical Price Trend (Avg per Year)",
            labels={"year": "Year", "avg_price": "Avg Price (DT)"},
            color_discrete_sequence=["#3b82f6"],
        )
        fig_line.update_traces(
            line_shape="spline", 
            line=dict(width=3, color="#3b82f6"),
            fillcolor="rgba(59, 130, 246, 0.1)",
            mode="lines"
        )
        fig_line.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False, color="#888888"),
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(128,128,128,0.1)",
                griddash="dash",
                color="#888888",
                zeroline=False
            ),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ── 5. Mileage Scatter ──────────────────────────────────────────────────
    st.markdown('<div class="section-title">5. Mileage vs Price Correlation</div>', unsafe_allow_html=True)
    scatter_df = df.dropna(subset=["price", "km"])
    scatter_df = scatter_df[(scatter_df["km"] <= 600000) & (scatter_df["price"] <= 600000)]
    
    if not scatter_df.empty:
        fig_scatter = px.scatter(
            scatter_df, x="km", y="price",
            color="year",
            hover_data=["title", "brand"],
            title="Price vs Mileage Scatter Plot",
            labels={"km": "Mileage (km)", "price": "Price (DT)", "year": "Year"},
            color_continuous_scale=["#b300ff", "#e94560", "#00d4ff"],
            opacity=0.7,
            render_mode="webgl"
        )
        fig_scatter.update_traces(marker=dict(size=8))
        fig_scatter.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)
