import re

def extract_entities(user_text, available_brands, available_fuels, available_locations=None, available_models=None):
    text_lower = user_text.lower()
    
    entities = {'year': None, 'km': None, 'brand': None, 'fuel': None, 'model': None, 'location': None}
    
    # 1. Extract Year (1980 - 2029)
    year_match = re.search(r'\b(19[8-9]\d|20[0-2]\d)\b', text_lower)
    if year_match:
        entities['year'] = int(year_match.group(1))
        
    # 2. Extract KM/Miles
    km_match = re.search(r'(\d{1,3}(?:[\s\.]?\d{3})*)\s*(km|k|kilometre|kilomètre|miles|mile|m|mi)\b', text_lower)
    if km_match:
        val_str = km_match.group(1).replace(' ', '').replace('.', '')
        km_val = int(val_str)
        if km_match.group(2) == 'k':
            km_val *= 1000
        entities['km'] = km_val
    else:
        # Fallback: look for generic big numbers
        large_nums = re.findall(r'\b([1-9]\d{3,5})\b', text_lower)
        for num_str in large_nums:
            val = int(num_str)
            # Make sure this isn't the extracted year!
            if entities['year'] is None or val != entities['year']:
                entities['km'] = val
                break
                
    # 3. Extract Brand
    # Sort brands by length descending so "Alfa Romeo" matches before "Alfa"
    sorted_brands = sorted([str(b) for b in available_brands if str(b) != 'nan'], key=len, reverse=True)
    for brand in sorted_brands:
        if brand.lower() in text_lower:
            entities['brand'] = brand
            break
            
    # Alias mapping for smarter brand recognition
    if not entities['brand']:
        aliases = {
            "benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz", "merc": "Mercedes-Benz",
            "vw": "Volkswagen", "volks": "Volkswagen", "bimmer": "BMW", "beamer": "BMW",
            "toy": "Toyota", "peug": "Peugeot", "pug": "Peugeot", "reno": "Renault"
        }
        for alias, real_brand in aliases.items():
            if alias in text_lower:
                entities['brand'] = real_brand
                break
                
    # 3.5 Extract Model
    if available_models:
        sorted_models = sorted([str(m) for m in available_models if str(m) != 'nan' and len(str(m)) > 2], key=len, reverse=True)
        for model in sorted_models:
            if model.lower() in text_lower:
                entities['model'] = model
                break
            
    # 3.7 Extract Location (New)
    if available_locations:
        sorted_locs = sorted([str(l) for l in available_locations if str(l) != 'nan'], key=len, reverse=True)
        for loc in sorted_locs:
            if loc.lower() in text_lower:
                entities['location'] = loc
                break

    # 4. Extract Fuel
    sorted_fuels = sorted([str(f) for f in available_fuels if str(f) != 'nan'], key=len, reverse=True)
    for fuel in sorted_fuels:
        if fuel.lower() in text_lower:
            entities['fuel'] = fuel
            break
            
    # Fallback to English synonyms if not directly matched to dataset tags
    if not entities['fuel']:
        if 'petrol' in text_lower or 'gas' in text_lower:
            # Map back to available fuels if possible, otherwise hardcode
            if 'Gasoline' in available_fuels:
                entities['fuel'] = 'Gasoline'
            
    return entities

def extract_intent_and_entities(user_text, available_brands, available_fuels, available_locations=None, available_models=None):
    """Detects if the user wants to predict a price or query live market stats."""
    entities = extract_entities(user_text, available_brands, available_fuels, available_locations, available_models)
    
    text_lower = user_text.lower()
    intent = "predict"
    
    if any(w in text_lower for w in ["cheapest", "lowest", "minimum", "min"]):
        intent = "min_price"
    elif any(w in text_lower for w in ["expensive", "highest", "maximum", "max"]):
        intent = "max_price"
    elif any(w in text_lower for w in ["how many", "count", "amount of", "total"]):
        intent = "count"
    elif any(w in text_lower for w in ["median", "average", "avg", "mean"]):
        intent = "avg_price"
        
    return intent, entities
