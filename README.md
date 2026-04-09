# 🚗 Auto Scraper TN — Market Intelligence Dashboard

A premium, professional-grade car market analysis and price prediction platform for the Tunisian automotive market. 

![Market Dashboard](https://img.shields.io/badge/Status-Production--Ready-brightgreen)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/Framework-Streamlit-red)

## 🌟 Key Features

- **Turbo-Charged Scraper**: Multi-threaded request engine collecting 150+ pages of automotive data in seconds.
- **Autonomous Intelligence**: 6-hour background synchronization engine that keeps market data fresh without manual intervention.
- **AI Market Bargain Hunter**: Automatically identifies vehicles priced ≥15% below their AI-estimated fair market value.
- **Glassmorphism UI**: High-end visual aesthetic with hardware-accelerated (WebGL) charts for zero-lag interaction.
- **AI Data Agent**: Interactive NLP chatbot for live market querying and specific vehicle discovery.
- **Precision ML Estimator**: High-accuracy price predictions using Gradient Boosting algorithms.
- **System Stability**: Global multi-session synchronization lock to prevent race conditions during deep crawls.

## 🛠️ Tech Stack

- **Dashboard**: [Streamlit](https://streamlit.io/)
- **Visuals**: [Plotly](https://plotly.com/) (with WebGL acceleration)
- **Data Engine**: [Pandas](https://pandas.pydata.org/), [SQLite](https://sqlite.org/)
- **AI/ML**: [Scikit-Learn](https://scikit-learn.org/) ($HistGradientBoostingRegressor$)
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

- `app.py`: Main router and autonomous background sync coordinator.
- `ui/`: Modular package for high-fidelity interface components.
- `scraper.py`: Turbo HTTP engine with global concurrency locking.
- `analyzer.py`: Statistics engine and market bargain discovery logic.
- `predictor.py`: Machine Learning models for price estimation.
- `market_intelligence_report.md`: Deep technical documentation on system architecture.

---
*Developed for Portfolio Excellence | Data Sourced from automobile.tn*

## Headless scraping

- The scraper uses Selenium and prefers Chrome via Selenium Manager. If Chrome is not available it will try Edge or fall back to a managed driver.
- To run the scraper in headless mode (no browser window), ensure dependencies are installed and run:

```bash
python -c "from scraper import scrape_cars; df = scrape_cars(3); df.to_csv('data/cars.csv', index=False)"
```

- If you plan to run this on a server or CI, make sure a browser binary (Chrome/Edge) is installed, or configure a container with one. For a GitHub Actions job, use an image that includes Chrome or install it during the job.

