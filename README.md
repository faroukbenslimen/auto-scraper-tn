# 🚗 Auto Scraper Tunisie — Projet Python

Application complète de **web scraping, analyse et prédiction** d'annonces automobiles d'occasion.
**Site cible :** automobile.tn

---

## 📁 Structure du projet

```
auto_project/
├── app.py              # Dashboard Streamlit (interface principale)
├── scraper.py          # Collecte HTTP + parsing HTML
├── cleaner.py          # Nettoyage des données
├── analyzer.py         # Statistiques & analyses
├── predictor.py        # Modèles IA (Random Forest + tendance)
├── requirements.txt    # Dépendances Python
└── data/
    └── cars.csv        # Données sauvegardées (créé automatiquement)
```

---

## ⚙️ Installation

```bash
# 1. Cloner / décompresser le projet
cd auto_project

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt
```

---

## 🚀 Lancement

```bash
streamlit run app.py
```

L'application s'ouvre automatiquement sur `http://localhost:8501`

---

## 🧩 Fonctionnalités

### 🏠 Accueil
- KPIs : total annonces, prix médian, prix min/max, marques, villes
- Top 5 / Bottom 5 : plus chères, moins chères, plus récentes, moins de km

### 📊 Résultats & Filtres
- Filtres : marque, carburant, ville, fourchette de prix, année
- Tableau des annonces filtré
- Export CSV

### 📈 Visualisations (5 graphiques)
1. Histogramme de distribution des prix
2. Box plot prix par carburant
3. Top 10 marques (annonces + prix moyen)
4. Pie chart répartition carburant
5. Courbe prix moyen par année
6. Scatter corrélation prix / kilométrage

### 🤖 Prédiction IA
- **Estimateur de prix** (Random Forest) : prédit le prix d'un véhicule à partir de l'année, km, marque, carburant
- **Tendance temporelle** (Régression Linéaire) : prédit l'évolution du prix moyen sur les N prochains jours

---

## 📌 Notes importantes

- Le scraping respecte un délai de 1.5s entre les requêtes
- Toutes les erreurs sont gérées avec try/except
- Les données sont fusionnées (pas de doublons) à chaque scraping
- Si le site cible change de structure HTML, ajuster les sélecteurs dans `scraper.py`

---

## 🛠️ Ajustement des sélecteurs HTML

Si le scraping ne retourne pas de données, ouvrir `scraper.py` et modifier la fonction `extract_car()` :
```python
# Inspecter l'élément sur le site cible (F12 → DevTools)
title_tag  = item.find("h2")                    # ou item.find(class_="car-title")
price_tag  = item.find(class_="price")          # adapter selon le site
year_tag   = item.find(class_="year")
km_tag     = item.find(class_="mileage")
```
