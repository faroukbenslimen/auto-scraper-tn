import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from predictor import CarPricePredictor, PriceTrendPredictor
from .ui_utils import render_styled_table

def render_ai_page(df):
    st.title("🤖 AI Intelligence Hub")

    if df.empty:
        st.info("👈 Run scraping first.")
        st.stop()

    tab1, tab2 = st.tabs(["🔮 Smarter AI Assistant", "📉 Forecasting Trends"])

    # ── Onglet 1 : Assistant IA ─────────────────────────────────────────
    with tab1:
        st.subheader("💬 Market Intelligence Assistant")
        st.info("Ask the AI anything about your data. Examples:\n- *'Estimate a 2018 Golf with 50k km'*\n- *'What is the cheapest Audi?'*\n- *'Average price of 2020 Peugeot'*\n- *'How many listings in Sousse?'*")

        @st.cache_resource
        def get_trained_predictor(_df):
            p = CarPricePredictor()
            p.train(_df)
            return p
            
        predictor = get_trained_predictor(df)
        metrics = predictor.metrics

        if "messages" not in st.session_state:
            st.session_state.messages = []
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "Hello! I am the Auto Scraper AI. 🤖 Which car or market trend would you like to analyze today?"
            })
            
        if "car_context" not in st.session_state:
            st.session_state.car_context = {"year": None, "km": None, "brand": None, "fuel": None, "model": None, "location": None}

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Describe the car or ask a question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            brands_list = sorted(df["brand"].dropna().unique().tolist())
            fuel_list = sorted(df["fuel"].dropna().unique().tolist())
            locs_list = sorted(df["location"].dropna().unique().tolist())
            models_list = sorted(df["title"].dropna().unique().tolist())
            
            from chat_helper import extract_intent_and_entities
            intent, extracted = extract_intent_and_entities(prompt, brands_list, fuel_list, locs_list, models_list)

            for k, v in extracted.items():
                if v is not None:
                    st.session_state.car_context[k] = v

            # --- BRAND INFERENCE LOGIC ---
            if st.session_state.car_context["brand"] is None and st.session_state.car_context["model"] is not None:
                model_name = st.session_state.car_context["model"]
                # Search for the most common brand for this title in the dataset
                inferred_brand = df[df["title"] == model_name]["brand"].mode()
                if not inferred_brand.empty:
                    st.session_state.car_context["brand"] = inferred_brand.iloc[0]
                    # Tag this as an assumption later
                    if "inferred_brand" not in st.session_state: st.session_state.inferred_brand = True
            else:
                st.session_state.inferred_brand = False

            ctx = st.session_state.car_context

            with st.chat_message("assistant"):
                # Logic pivot: Market Stats vs ML Prediction
                if intent == "predict" and ctx["brand"] and not ctx["year"]:
                    query_df = df[df["brand"] == ctx["brand"]]
                    if not query_df.empty:
                        intent = "avg_price"

                if intent != "predict":
                    # Data Agent logic
                    query_df = df.dropna(subset=["price"]).copy()
                    filters_applied = []
                    if ctx["brand"]: 
                        query_df = query_df[query_df["brand"] == ctx["brand"]]
                        filters_applied.append(f"**{ctx['brand']}**")
                    if ctx["model"]: 
                        query_df = query_df[query_df["title"].str.contains(ctx["model"], case=False, na=False)]
                        filters_applied.append(f"**{ctx['model']}**")
                    if ctx["year"]: 
                        query_df = query_df[query_df["year"] == ctx["year"]]
                        filters_applied.append(f"year **{int(ctx['year'])}**")
                    
                    filter_str = " ".join(filters_applied) if filters_applied else "the market"

                    if query_df.empty:
                        response_text = f"I couldn't find any exact listings for {filter_str}. Try broading your search!"
                    elif intent == "count":
                        response_text = f"I found **{len(query_df)}** listings for {filter_str}."
                    elif intent == "min_price":
                        min_row = query_df.loc[query_df["price"].idxmin()]
                        response_text = f"The cheapest {filter_str} is a **{int(min_row['year'])} {min_row['title']}** at **{int(min_row['price']):,} DT**.\n\n🔗 [View Listing]({min_row.get('link','#')})"
                    elif intent == "max_price":
                        max_row = query_df.loc[query_df["price"].idxmax()]
                        response_text = f"The most premium {filter_str} is a **{int(max_row['year'])} {max_row['title']}** at **{int(max_row['price']):,} DT**.\n\n🔗 [View Listing]({max_row.get('link','#')})"
                    elif intent == "avg_price":
                        avg_p = query_df["price"].mean()
                        response_text = f"Based on {len(query_df)} listings, the average price for {filter_str} is approximately **{int(avg_p):,} DT**.\n\n"
                        
                        # Add a few example links
                        examples = query_df.sort_values("price").head(3)
                        response_text += "✨ **Featured Listings:**\n"
                        for _, row in examples.iterrows():
                            l = row.get("link", "#")
                            response_text += f"- [{row['title']} ({int(row['year'])})]({l}) — **{int(row['price']):,} DT**\n"
                        
                        response_text += f"\n👉 You can examine all {len(query_df)} results in the **Results** tab!"
                        
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                    st.session_state.car_context = {"year": None, "km": None, "brand": None, "fuel": None, "model": None}
                else:
                    if not ctx["brand"] and not ctx["model"]:
                        response = "I need a **brand** or **model** to perform an AI estimation. What are you looking for?"
                        st.markdown(response)
                        st.session_state.messages.append({"role": "assistant", "content": response})
                    else:
                        assumptions_made = []
                        if st.session_state.get("inferred_brand"):
                            assumptions_made.append(f"Brand: **{ctx['brand']}**")
                        
                        if not ctx["brand"]:
                            # Fallback if inference failed but model exists
                            ctx["brand"] = "Volkswagen" # Default fallback for the region if totally unknown
                            assumptions_made.append(f"Brand: **{ctx['brand']}** (Estimated)")

                        if not ctx["year"]:
                            brand_data = df[df["brand"] == ctx["brand"]]
                            ctx["year"] = int(brand_data["year"].median()) if not brand_data.empty else 2019
                            assumptions_made.append(f"year {ctx['year']}")
                        if not ctx["km"]:
                            ctx["km"] = (2024-ctx["year"])*15000 if ctx["year"] else 50000
                            assumptions_made.append(f"{ctx['km']:,} km")
                        if not ctx["fuel"]:
                            ctx["fuel"] = "Gasoline"
                            assumptions_made.append("Gasoline")

                        with st.spinner("AI Brain Thinking..."):
                            import time; time.sleep(0.8)
                            # Pass location to the upgraded precision model
                            pred_loc = ctx["location"] if ctx["location"] else "Tunis"
                            result = predictor.predict_range(ctx["year"], ctx["km"], ctx["brand"], ctx["fuel"], pred_loc)
                            p = int(result['predicted'])
                            l, h = int(result['low']), int(result['high'])
                            
                            loc_title = f" in {pred_loc}" if ctx["location"] else ""
                            fig = go.Figure(go.Indicator(
                                mode="number+gauge", value=p,
                                number={'prefix': "DT ", 'font': {'size': 35, 'color': '#00d4ff'}},
                                title={'text': f"<b>{ctx['brand']}{loc_title}</b><br><span style='font-size:0.8em;color:gray'>({ctx['year']} | {ctx['km']:,} km)</span>", 'font': {'size': 18}},
                                gauge={'shape': "bullet", 'axis': {'range': [l*0.8, h*1.2]}, 'bar': {'color': "#00d4ff"}}
                            ))
                            fig.update_layout(height=160, margin={'t': 40, 'b': 20, 'l': 80, 'r': 10}, paper_bgcolor='rgba(0,0,0,0)')
                            
                            note = f"\n\n*(Assumptions: {', '.join(assumptions_made)} used for this estimate)*" if assumptions_made else ""
                            resp = f"🏎️ AI predicts a value of **{p:,} DT** (Market: {l:,} - {h:,} DT).{note}"
                            st.markdown(resp)
                            st.plotly_chart(fig, use_container_width=True)
                            st.session_state.messages.append({"role": "assistant", "content": resp})
                            st.session_state.car_context = {"year": None, "km": None, "brand": None, "fuel": None, "model": None}

        with st.expander("⚙️ Advanced AI Metrics"):
            if "error" not in metrics and metrics.get("train_size", 0) > 0:
                c1, c2, c3 = st.columns(3)
                mae = metrics.get('mae', 0)
                mae_str = f"{int(mae):,} DT" if mae > 0 else "—"
                c1.metric("MAE", mae_str)
                c2.metric("R² Score", f"{metrics.get('r2', 0):.3f}")
                c3.metric("Dataset Size", f"{metrics.get('train_size', 0)}")
            else:
                st.info("Train the model with more data to see accuracy metrics.")

    # ── Onglet 2 : Tendance temporelle ────────────────────────────────────────
    with tab2:
        st.subheader("📉 Market Forecasting")
        days = st.slider("Forecast Horizon (Days)", 7, 30, 14)
        @st.cache_resource
        def get_trained_trend_model(_df):
            m = PriceTrendPredictor()
            m.train(_df)
            return m
            
        m = get_trained_trend_model(df)
        f_df = m.get_full_history_with_prediction(days=days)
        h_df, p_df = f_df[f_df["type"]=="History"], f_df[f_df["type"]=="Prediction"]

        fig = go.Figure()
        
        # 1. Background History Area (Minimalist Style)
        fig.add_trace(go.Scatter(
            x=h_df["date"], y=h_df["predicted_price"],
            name="Market History",
            mode="lines",
            line=dict(color="#3b82f6", width=3, shape="spline", smoothing=1.3),
            fill="tozeroy",
            fillcolor="rgba(59, 130, 246, 0.1)",
            hovertemplate="<b>%{x}</b><br>Average: %{y:,.0f} DT<extra></extra>"
        ))

        # 2. Prediction / Forecast (Dashed Blue Glow)
        fig.add_trace(go.Scatter(
            x=p_df["date"], y=p_df["predicted_price"],
            name="AI Prediction",
            mode="lines",
            line=dict(color="#3b82f6", width=2, dash="dash", shape="spline", smoothing=1.3),
            hovertemplate="<b>Forecast</b><br>%{x}: %{y:,.0f} DT<extra></extra>"
        ))

        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                showgrid=False, 
                color="#888888",
                tickformat="%m/%d",
                dtick="D3" # Show tick every 3 days to match reference
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(128,128,128,0.1)",
                griddash="dash", # Dashed grid lines like in reference
                color="#888888",
                zeroline=False,
                side="left"
            ),
            legend=dict(
                orientation="h", x=0, y=1.1, xanchor="left",
                font=dict(color="#888888", size=12)
            ),
            margin=dict(t=60, b=40, l=40, r=20),
            height=400,
            hovermode="x"
        )
        st.plotly_chart(fig, use_container_width=True)
        render_styled_table(p_df[["date", "predicted_price"]].reset_index(drop=True))
