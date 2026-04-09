import pandas as pd
from chat_helper import extract_intent_and_entities

# Mock data
df = pd.DataFrame({
    'title': ['Volkswagen Golf 8 R', 'Renault Clio 4', 'Peugeot 208', 'Audi A3'],
    'brand': ['Volkswagen', 'Renault', 'Peugeot', 'Audi'],
    'fuel': ['Gasoline', 'Diesel', 'Gasoline', 'Diesel'],
    'location': ['Tunis', 'Sousse', 'Sfax', 'Ariana'],
    'year': [2022, 2018, 2020, 2015]
})

brands = df['brand'].unique().tolist()
fuels = df['fuel'].unique().tolist()
locs = df['location'].unique().tolist()
models = df['title'].unique().tolist()

test_cases = [
    "golf 8 R",
    "clio 4 in sousse",
    "estimate a 2018 audi a3",
    "vw golf diesel",
    "2020 peug 208"
]

print("--- NLP Test Results ---")
for cmd in test_cases:
    intent, entities = extract_intent_and_entities(cmd, brands, fuels, locs, models)
    
    # Simulate Brand Inference
    if entities['brand'] is None and entities['model'] is not None:
        inferred = df[df['title'] == entities['model']]['brand'].mode()
        if not inferred.empty:
            entities['brand'] = inferred.iloc[0]
            entities['inferred'] = True
    
    print(f"Input: '{cmd}'")
    print(f"  Detected -> Brand: {entities.get('brand')}, Model: {entities.get('model')}, Year: {entities.get('year')}, Inferred: {entities.get('inferred', False)}")
    print("-" * 30)
