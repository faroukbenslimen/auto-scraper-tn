import streamlit as st
import pandas as pd
import os
import plotly.io as pio

def detect_dark_mode():
    config_path = os.path.join(".streamlit", "config.toml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return 'base="light"' not in f.read()
    return True

def setup_plotly_theme(is_dark):
    if is_dark:
        template = pio.templates["plotly_dark"]
        pio.templates.default = "plotly_dark"
    else:
        template = pio.templates["plotly_white"]
        pio.templates.default = "plotly_white"
    
    template.layout.paper_bgcolor = "rgba(0,0,0,0)"
    template.layout.plot_bgcolor = "rgba(0,0,0,0)"
    template.layout.colorway = ["#00d4ff", "#e94560", "#b300ff", "#ff007f", "#39ff14", "#ffff00"]

def apply_custom_css(is_dark):
    if is_dark:
        sidebar_bg = "linear-gradient(180deg, #0a0a0f 0%, #14141f 100%)"
        metric_bg = "rgba(255, 255, 255, 0.03)"
        border_color = "rgba(255, 255, 255, 0.08)"
        hover_shadow = "rgba(0, 212, 255, 0.15)"
        text_color = "#ffffff"
    else:
        sidebar_bg = "linear-gradient(180deg, #f0f2f6 0%, #e8eaef 100%)"
        metric_bg = "rgba(0, 0, 0, 0.03)"
        border_color = "rgba(0, 0, 0, 0.1)"
        hover_shadow = "rgba(0, 212, 255, 0.3)"
        text_color = "#31333F"

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        
        html, body, [class*="css"] {{ font-family: 'Inter', sans-serif !important; }}
        .block-container {{ padding-top: 2rem !important; padding-bottom: 2rem !important; }}
        header {{visibility: hidden;}}
        
        [data-testid="stSidebar"] {{ background: {sidebar_bg} !important; border-right: 1px solid {border_color}; }}
        
        .metric-card {{
            background: {metric_bg};
            backdrop-filter: blur(16px);
            border: 1px solid {border_color};
            border-radius: 16px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 40px {hover_shadow};
            border: 1px solid rgba(0, 212, 255, 0.3);
        }}
        .metric-value {{ 
            font-size: 2.2rem; font-weight: 700; 
            background: -webkit-linear-gradient(45deg, #00d4ff, #e94560);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }}
        .metric-label {{ font-size: 0.85rem; color: #a0a0b0; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }}
        
        .section-title {{
            font-size: 1.6rem; font-weight: 700; border-left: 5px solid #00d4ff; padding: 10px 0 10px 15px;
            margin: 30px 0 20px 0; color: {text_color};
            background: linear-gradient(90deg, rgba(0, 212, 255, 0.1) 0%, rgba(0,0,0,0) 100%);
            border-radius: 0 8px 8px 0;
        }}
        
        .stButton > button {{
            background: linear-gradient(135deg, #e94560 0%, #b300ff 100%);
            color: white; border: none; border-radius: 50px; padding: 10px 24px; font-weight: 600;
            width: 100%; transition: all 0.3s ease; box-shadow: 0 4px 15px rgba(233, 69, 96, 0.4);
        }}
        .stButton > button:hover {{ transform: translateY(-2px); box-shadow: 0 8px 25px rgba(233, 69, 96, 0.6); color: white; }}
        
        hr {{ border-top: none; height: 2px; background: linear-gradient(90deg, transparent, rgba(0, 212, 255, 0.5), transparent); margin: 2rem 0; }}
        
        .glass-table-container {{
            background: {metric_bg}; backdrop-filter: blur(16px); border: 1px solid {border_color};
            border-radius: 12px; padding: 5px 15px 15px 15px; box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
            margin-bottom: 20px; overflow-x: auto; max-height: 500px;
        }}
        .glass-table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
        .glass-table th {{ text-align: left; padding: 12px 10px; color: #a0a0b0; font-weight: 600; text-transform: uppercase; font-size: 0.75rem; border-bottom: 1px solid {border_color}; }}
        .glass-table td {{ padding: 12px 10px; border-bottom: 1px solid {border_color}; }}
        .glass-table tr:hover {{ background: {hover_shadow}; transition: background 0.3s ease; }}
    </style>
    """, unsafe_allow_html=True)

def render_styled_table(df, paginate=False, page_size=20, table_id="default_table"):
    rename_cols = {
        "image_url": "Photo", "title": "Model / Title", "brand": "Brand", "year": "Year",
        "price": "Price", "km": "Mileage", "fuel": "Fuel", "location": "Location",
        "date": "Date", "predicted_price": "Predicted Price (DT)"
    }
    display_df = df.copy()

    if paginate and len(display_df) > page_size:
        total_pages = (len(display_df) - 1) // page_size + 1
        page_key = f"pagination_{table_id}"
        if page_key not in st.session_state: st.session_state[page_key] = 1
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            if st.button("⬅️ Preview", key=f"{page_key}_prev", disabled=st.session_state[page_key] <= 1):
                st.session_state[page_key] -= 1
                st.rerun()
        with c2:
            st.markdown(f"<div style='text-align: center; margin-top: 5px; font-weight: 500;'>Page {st.session_state[page_key]} / {total_pages}</div>", unsafe_allow_html=True)
        with c3:
            if st.button("Next ➡️", key=f"{page_key}_next", disabled=st.session_state[page_key] >= total_pages):
                st.session_state[page_key] += 1
                st.rerun()
        start_idx = (st.session_state[page_key] - 1) * page_size
        display_df = display_df.iloc[start_idx : start_idx + page_size].copy()

    if not display_df.empty:
        display_df = display_df.rename(columns=rename_cols)
        if "Photo" in display_df.columns:
            display_df["Photo"] = display_df["Photo"].apply(
                lambda url: f'<img src="{url}" width="85" style="border-radius:6px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">' 
                if pd.notnull(url) and str(url).startswith("http") else ""
            )
        for col in ["Year", "Price", "Mileage", "Predicted Price (DT)"]:
            if col in display_df.columns:
                if col == "Year":
                    display_df[col] = display_df[col].apply(lambda x: f"{int(x)}" if pd.notnull(x) else "")
                elif col == "Price" or col == "Predicted Price (DT)":
                    display_df[col] = display_df[col].apply(lambda x: f"{int(x):,} DT".replace(",", " ") if pd.notnull(x) else "")
                elif col == "Mileage":
                    display_df[col] = display_df[col].apply(lambda x: f"{int(x):,} km".replace(",", " ") if pd.notnull(x) else "")
            
    html = display_df.to_html(classes="glass-table", index=False, justify="left", escape=False)
    html = html.replace('border="1"', '')
    st.markdown(f'<div class="glass-table-container">{html}</div>', unsafe_allow_html=True)
