# 🚗 Auto Scraper TN — Market Intelligence Dashboard

A premium, professional-grade car market analysis and price prediction platform for the Tunisian automotive market. 

![Market Dashboard](https://img.shields.io/badge/Status-Production--Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)

## 🌟 Key Features

- **Turbo-Charged Scraper**: Multi-threaded request engine collecting 150+ pages of automotive data in seconds (replaces legacy Selenium).
- **Glassmorphism UI**: High-end visual aesthetic with instantaneous Dark/Light mode toggling and fluid page transitions.
- **AI Data Agent**: Interactive NLP chatbot that answers questions about the live market, finds specific vehicles, and provides direct links.
- **Precision ML Estimator**: Gradient Boosting model ($HistGradientBoostingRegressor$) trained on live market data for high-accuracy price predictions.
- **Market Forecasting**: Time-series analysis predicting price trends for the next 14-30 days.
- **SQL Backend**: Robust data persistence using SQLite for historical tracking and zero-duplicate indexing.

## 🛠️ Tech Stack

- **Dashboard**: [Streamlit](https://streamlit.io/)
- **Visuals**: [Plotly](https://plotly.com/)
- **Data Engine**: [Pandas](https://pandas.pydata.org/), [SQLite](https://sqlite.org/)
- **AI/ML**: [Scikit-Learn](https://scikit-learn.org/)
- **NLP**: Custom Intent Classification + Fuzzy Entity Extraction

## 🚀 Rapid Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Launch the Dashboard**:
   ```bash
   streamlit run app.py
   ```

## 📁 Project Architecture

- `app.py`: Main router and application entry point.
- `ui/`: Modular interface components.
  - `ui_home.py`: Market Intelligence KPI dashboard.
  - `ui_results.py`: Advanced filtering and results explorer.
  - `ui_visuals.py`: High-fidelity data visualizations.
  - `ui_ai.py`: AI Assistant and Market Trends logic.
- `scraper.py`: Concurrent scraping engine.
- `predictor.py`: ML models for regression and forecasting.
- `chat_helper.py`: NLP intelligence for the chatbot.

---
*Developed for Portfolio Excellence | Data Sourced from automobile.tn*
