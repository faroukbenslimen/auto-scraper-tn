"""
app.py — Dashboard Streamlit : Scraping Automobiles Tunisie
Lancez avec : streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

from scraper import scrape_cars, save_data, load_data
from cleaner import clean_dataframe
from analyzer import (
    full_summary, by_brand, by_fuel, by_location, by_year,
    price_distribution_bins, top5_expensive, bottom5_cheapest,
)
from predictor import CarPricePredictor, PriceTrendPredictor

# ─── Configuration page ───────────────────────────────────────────────────────

st.set_page_config(
    page_title="🚗 Auto Scraper Tunisie",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styles CSS ───────────────────────────────────────────────────────────────

st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin: 5px;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #e94560; }
    .metric-label { font-size: 0.85rem; color: #a0a0b0; margin-top: 4px; }
    .section-title {
        font-size: 1.4rem; font-weight: 600;
        border-left: 4px solid #e94560;
        padding-left: 10px; margin: 20px 0 10px 0;
    }
    .stButton > button {
        background: linear-gradient(135deg, #e94560, #c23152);
        color: white; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; font-size: 1rem;
        width: 100%; transition: 0.3s;
    }
    .stButton > button:hover { opacity: 0.85; transform: scale(1.02); }
</style>
""", unsafe_allow_html=True)


# ─── Données en cache ─────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def get_data():
    df_raw = load_data()
    if df_raw.empty:
        return pd.DataFrame()
    return clean_dataframe(df_raw)


def refresh_data():
    st.cache_data.clear()


# ─── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Flag_of_Tunisia.svg/32px-Flag_of_Tunisia.svg.png", width=30)
    st.title("🚗 Auto Scraper TN")
    st.markdown("---")

    page = st.radio(
        "Navigation",
        ["🏠 Accueil", "📊 Résultats & Filtres", "📈 Visualisations", "🤖 Prédiction IA"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.subheader("⚙️ Paramètres du scraping")
    num_pages = st.slider("Nombre de pages", 1, 20, 5)

    if st.button("🔄 Lancer le scraping"):
        with st.spinner("Scraping en cours…"):
            try:
                df_raw = scrape_cars(num_pages=num_pages)
                if not df_raw.empty:
                    save_data(df_raw)
                    refresh_data()
                    st.success(f"✅ {len(df_raw)} annonces collectées !")
                else:
                    st.warning("⚠️ Aucune annonce trouvée.")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")

    if st.button("🗑️ Effacer les données"):
        if os.path.exists("data/cars.csv"):
            os.remove("data/cars.csv")
            refresh_data()
            st.info("Données supprimées.")

    st.markdown("---")
    st.caption("Projet Python — SESAME Technology\nSource : automobile.tn")


# ─── Chargement données ───────────────────────────────────────────────────────

df = get_data()
has_data = not df.empty


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 1 — ACCUEIL
# ═══════════════════════════════════════════════════════════════════════════════

if page == "🏠 Accueil":
    st.title("🚗 Tableau de bord — Automobiles Tunisie")
    st.markdown("Application de collecte et d'analyse d'annonces automobiles d'occasion.")

    if not has_data:
        st.info("👈 Cliquez sur **Lancer le scraping** dans la barre latérale pour collecter des données.")
        st.stop()

    summary = full_summary(df)

    # ── KPI Cards ────────────────────────────────────────────────────────────
    col1, col2, col3, col4 = st.columns(4)
    ps = summary["price_stats"]

    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{summary['total_annonces']}</div>
            <div class="metric-label">Total annonces</div></div>""", unsafe_allow_html=True)
    with col2:
        val = f"{int(ps.get('median', 0)):,} DT" if ps else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Prix médian</div></div>""", unsafe_allow_html=True)
    with col3:
        val = f"{int(ps.get('min', 0)):,} DT" if ps else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Prix minimum</div></div>""", unsafe_allow_html=True)
    with col4:
        val = f"{int(ps.get('max', 0)):,} DT" if ps else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Prix maximum</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    ys = summary["year_stats"]
    ks = summary["km_stats"]

    with col5:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{summary['marques_uniques']}</div>
            <div class="metric-label">Marques distinctes</div></div>""", unsafe_allow_html=True)
    with col6:
        val = f"{int(ys.get('newest', 0))}" if ys else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Année max</div></div>""", unsafe_allow_html=True)
    with col7:
        val = f"{int(ks.get('median', 0)):,} km" if ks else "—"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">Kilométrage médian</div></div>""", unsafe_allow_html=True)
    with col8:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-value">{summary['villes_uniques']}</div>
            <div class="metric-label">Villes couvertes</div></div>""", unsafe_allow_html=True)

    # ── Top 5 / Bottom 5 ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🏆 Top 5 & Bottom 5</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("💰 Les plus chères")
        st.dataframe(summary["top5_expensive"], use_container_width=True, hide_index=True)

    with col_b:
        st.subheader("🤑 Les moins chères")
        st.dataframe(summary["bottom5_cheapest"], use_container_width=True, hide_index=True)

    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("✨ Les plus récentes")
        st.dataframe(summary["top5_newest"], use_container_width=True, hide_index=True)
    with col_d:
        st.subheader("📉 Le moins de km")
        st.dataframe(summary["top5_low_km"], use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 2 — RÉSULTATS & FILTRES
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📊 Résultats & Filtres":
    st.title("📊 Résultats — Toutes les annonces")

    if not has_data:
        st.info("👈 Lancez le scraping d'abord.")
        st.stop()

    # ── Filtres ───────────────────────────────────────────────────────────────
    with st.expander("🎛️ Filtres", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            brands = ["Toutes"] + sorted(df["brand"].dropna().unique().tolist())
            selected_brand = st.selectbox("Marque", brands)

        with col2:
            fuels = ["Tous"] + sorted(df["fuel"].dropna().unique().tolist())
            selected_fuel = st.selectbox("Carburant", fuels)

        with col3:
            locations = ["Toutes"] + sorted(df["location"].dropna().unique().tolist())
            selected_loc = st.selectbox("Ville", locations)

        col4, col5 = st.columns(2)
        prices = df["price"].dropna()
        price_min, price_max = int(prices.min()) if not prices.empty else 0, int(prices.max()) if not prices.empty else 100000
        with col4:
            price_range = st.slider("Fourchette de prix (DT)", price_min, price_max, (price_min, price_max), step=500)

        years = df["year"].dropna()
        year_min, year_max = int(years.min()) if not years.empty else 2000, int(years.max()) if not years.empty else 2025
        with col5:
            year_range = st.slider("Année", year_min, year_max, (year_min, year_max))

    # ── Application des filtres ───────────────────────────────────────────────
    filtered = df.copy()
    if selected_brand != "Toutes":
        filtered = filtered[filtered["brand"] == selected_brand]
    if selected_fuel != "Tous":
        filtered = filtered[filtered["fuel"] == selected_fuel]
    if selected_loc != "Toutes":
        filtered = filtered[filtered["location"] == selected_loc]
    filtered = filtered[
        (filtered["price"].isna() | filtered["price"].between(price_range[0], price_range[1])) &
        (filtered["year"].isna() | filtered["year"].between(year_range[0], year_range[1]))
    ]

    st.markdown(f"**{len(filtered)}** annonce(s) correspondent aux filtres.")

    # ── Export CSV ────────────────────────────────────────────────────────────
    csv = filtered.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button("📥 Télécharger CSV", csv, "annonces_voitures.csv", "text/csv")

    # ── Tableau ───────────────────────────────────────────────────────────────
    display_cols = [c for c in ["title", "brand", "year", "price", "km", "fuel", "location"] if c in filtered.columns]
    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=500,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 3 — VISUALISATIONS
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "📈 Visualisations":
    st.title("📈 Visualisations")

    if not has_data:
        st.info("👈 Lancez le scraping d'abord.")
        st.stop()

    COLORS = px.colors.qualitative.Set2

    # ── 1. Distribution des prix ──────────────────────────────────────────────
    st.markdown('<div class="section-title">1. Distribution des prix</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        prices_clean = df["price"].dropna()
        fig_hist = px.histogram(
            prices_clean, nbins=30,
            title="Histogramme des prix (DT)",
            labels={"value": "Prix (DT)", "count": "Nombre"},
            color_discrete_sequence=["#e94560"],
        )
        fig_hist.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_hist, use_container_width=True)

    with col2:
        fig_box = px.box(
            df.dropna(subset=["price", "fuel"]),
            x="fuel", y="price", color="fuel",
            title="Prix par type de carburant",
            labels={"price": "Prix (DT)", "fuel": "Carburant"},
            color_discrete_sequence=COLORS,
        )
        fig_box.update_layout(showlegend=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_box, use_container_width=True)

    # ── 2. Top 10 marques ─────────────────────────────────────────────────────
    st.markdown('<div class="section-title">2. Top 10 marques</div>', unsafe_allow_html=True)
    brand_df = by_brand(df).head(10)

    col3, col4 = st.columns(2)
    with col3:
        fig_bar = px.bar(
            brand_df, x="brand", y="nb_annonces",
            title="Nombre d'annonces par marque",
            color="nb_annonces", color_continuous_scale="Reds",
            labels={"brand": "Marque", "nb_annonces": "Annonces"},
        )
        fig_bar.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col4:
        fig_bar2 = px.bar(
            brand_df.dropna(subset=["prix_moyen"]),
            x="brand", y="prix_moyen",
            title="Prix moyen par marque (DT)",
            color="prix_moyen", color_continuous_scale="Blues",
            labels={"brand": "Marque", "prix_moyen": "Prix moyen (DT)"},
        )
        fig_bar2.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_bar2, use_container_width=True)

    # ── 3. Répartition carburant ─────────────────────────────────────────────
    st.markdown('<div class="section-title">3. Répartition par carburant</div>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)

    fuel_df = by_fuel(df)
    with col5:
        fig_pie = px.pie(
            fuel_df, names="fuel", values="nb_annonces",
            title="Répartition par carburant",
            color_discrete_sequence=COLORS,
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col6:
        loc_df = by_location(df).head(10)
        fig_loc = px.bar(
            loc_df, x="nb_annonces", y="location", orientation="h",
            title="Top 10 villes",
            color="nb_annonces", color_continuous_scale="Greens",
            labels={"location": "Ville", "nb_annonces": "Annonces"},
        )
        fig_loc.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_loc, use_container_width=True)

    # ── 4. Évolution prix / année ─────────────────────────────────────────────
    st.markdown('<div class="section-title">4. Prix moyen par année de fabrication</div>', unsafe_allow_html=True)
    year_df = by_year(df)
    if not year_df.empty:
        fig_line = px.line(
            year_df, x="year", y="prix_moyen",
            markers=True,
            title="Évolution du prix moyen selon l'année du véhicule",
            labels={"year": "Année", "prix_moyen": "Prix moyen (DT)"},
            color_discrete_sequence=["#e94560"],
        )
        fig_line.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_line, use_container_width=True)

    # ── 5. Scatter prix vs km ─────────────────────────────────────────────────
    st.markdown('<div class="section-title">5. Corrélation Prix / Kilométrage</div>', unsafe_allow_html=True)
    scatter_df = df.dropna(subset=["price", "km"])
    if not scatter_df.empty:
        fig_scatter = px.scatter(
            scatter_df, x="km", y="price",
            color="brand" if "brand" in scatter_df.columns else None,
            hover_data=["title", "year"],
            title="Prix vs Kilométrage (par marque)",
            labels={"km": "Kilométrage (km)", "price": "Prix (DT)"},
            opacity=0.7,
        )
        fig_scatter.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_scatter, use_container_width=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE 4 — PRÉDICTION IA
# ═══════════════════════════════════════════════════════════════════════════════

elif page == "🤖 Prédiction IA":
    st.title("🤖 Prédiction IA — Prix & Tendances")

    if not has_data:
        st.info("👈 Lancez le scraping d'abord.")
        st.stop()

    tab1, tab2 = st.tabs(["🔮 Estimer un prix", "📉 Tendance temporelle"])

    # ── Onglet 1 : Estimateur de prix ─────────────────────────────────────────
    with tab1:
        st.subheader("🔮 Estimateur de prix par caractéristiques")
        st.info("Le modèle Random Forest analyse les données collectées pour estimer le prix d'un véhicule.")

        predictor = CarPricePredictor()
        with st.spinner("Entraînement du modèle…"):
            metrics = predictor.train(df)

        if "error" in metrics:
            st.error(metrics["error"])
        else:
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("MAE (Erreur moyenne)", f"{int(metrics['mae']):,} DT")
            col_m2.metric("R² Score", f"{metrics['r2']:.3f}")
            col_m3.metric("Données d'entraînement", f"{metrics['train_size']} annonces")

            st.markdown("---")
            st.subheader("Paramètres du véhicule")

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                year_input = st.number_input("Année", 2000, 2025, 2019)
            with c2:
                km_input = st.number_input("Kilométrage (km)", 0, 500000, 80000, step=5000)
            with c3:
                brands_list = sorted(df["brand"].dropna().unique().tolist())
                brand_input = st.selectbox("Marque", brands_list if brands_list else ["Toyota"])
            with c4:
                fuel_list = sorted(df["fuel"].dropna().unique().tolist())
                fuel_input = st.selectbox("Carburant", fuel_list if fuel_list else ["Diesel"])

            if st.button("🚀 Estimer le prix"):
                result = predictor.predict_range(year_input, km_input, brand_input, fuel_input)
                st.markdown("---")
                c_low, c_mid, c_high = st.columns(3)
                c_low.metric("Fourchette basse", f"{int(result['low']):,} DT")
                c_mid.metric("🎯 Prix estimé", f"{int(result['predicted']):,} DT", delta=None)
                c_high.metric("Fourchette haute", f"{int(result['high']):,} DT")

                conf = result["confidence"]
                color = "green" if conf > 0.7 else "orange" if conf > 0.4 else "red"
                st.markdown(f"**Indice de confiance :** :{color}[{conf:.0%}]")

            # ── Importance des features ───────────────────────────────────────
            if "feature_importance" in metrics:
                st.markdown("---")
                st.subheader("📊 Importance des variables")
                fi = pd.DataFrame({
                    "Variable": list(metrics["feature_importance"].keys()),
                    "Importance": list(metrics["feature_importance"].values()),
                }).sort_values("Importance", ascending=True)
                fig_fi = px.bar(fi, x="Importance", y="Variable", orientation="h",
                                color="Importance", color_continuous_scale="Reds")
                fig_fi.update_layout(coloraxis_showscale=False, plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_fi, use_container_width=True)

    # ── Onglet 2 : Tendance temporelle ────────────────────────────────────────
    with tab2:
        st.subheader("📉 Tendance du prix moyen & Prédiction")
        st.info("Analyse de l'évolution du prix moyen et prédiction des 14 prochains jours.")

        days_ahead = st.slider("Nombre de jours à prédire", 3, 30, 14)

        trend_model = PriceTrendPredictor()
        trend_model.train(df)
        full_df = trend_model.get_full_history_with_prediction(days=days_ahead)

        hist_df = full_df[full_df["type"] == "Historique"]
        pred_df = full_df[full_df["type"] == "Prédiction"]

        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(
            x=hist_df["date"].astype(str), y=hist_df["prix_predit"],
            name="Historique", line=dict(color="#e94560", width=2),
            mode="lines+markers",
        ))
        fig_trend.add_trace(go.Scatter(
            x=pred_df["date"].astype(str), y=pred_df["prix_predit"],
            name="Prédiction", line=dict(color="#00d4ff", width=2, dash="dash"),
            mode="lines+markers",
        ))
        fig_trend.update_layout(
            title="Évolution & prédiction du prix moyen (DT)",
            xaxis_title="Date", yaxis_title="Prix moyen (DT)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        st.subheader(f"📅 Prédictions pour les {days_ahead} prochains jours")
        st.dataframe(
            pred_df[["date", "prix_predit"]].rename(
                columns={"date": "Date", "prix_predit": "Prix prédit (DT)"}
            ).reset_index(drop=True),
            use_container_width=True,
        )
