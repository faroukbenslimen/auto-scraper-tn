import re

def extract_entities(user_text, available_brands, available_fuels, available_locations=None, available_models=None):
    text_lower = user_text.lower()
    
    entities = {'year': None, 'km': None, 'brand': None, 'fuel': None, 'model': None, 'location': None}
    
    # 1. Extract Year (1980 - 2029)
    year_match = re.search(r'\b(19[8-9]\d|20[0-2]\d)\b', text_lower)
    if year_match:
        entities['year'] = int(year_match.group(1))
        # Remove year from matching text to avoid interference
        text_lower = text_lower.replace(str(entities['year']), ' ')
        
    # 2. Extract KM
    km_match = re.search(r'(\d{1,3}(?:[\s\.]?\d{3})*)\s*(km|k|kilometre|kilomètre|miles|mile|m|mi)\b', text_lower)
    if km_match:
        val_str = km_match.group(1).replace(' ', '').replace('.', '')
        km_val = int(val_str)
        if km_match.group(2) == 'k':
            km_val *= 1000
        entities['km'] = km_val
        text_lower = text_lower.replace(km_match.group(0), ' ')
    else:
        large_nums = re.findall(r'\b([1-9]\d{3,5})\b', text_lower)
        for num_str in large_nums:
            val = int(num_str)
            if entities['year'] is None or val != entities['year']:
                entities['km'] = val
                text_lower = text_lower.replace(num_str, ' ')
                break
                
    # 3. Extract Fuel
    sorted_fuels = sorted([str(f) for f in available_fuels if str(f) != 'nan'], key=len, reverse=True)
    for fuel in sorted_fuels:
        if fuel.lower() in text_lower:
            entities['fuel'] = fuel
            text_lower = text_lower.replace(fuel.lower(), ' ')
            break
            
    # 3.1 Extract Brand
    sorted_brands = sorted([str(b) for b in available_brands if str(b) != 'nan'], key=len, reverse=True)
    for brand in sorted_brands:
        if brand.lower() in text_lower:
            entities['brand'] = brand
            text_lower = text_lower.replace(brand.lower(), ' ')
            break
            
    # Alias mapping for smarter brand recognition
    if not entities['brand']:
        aliases = {
            "benz": "Mercedes-Benz", "mercedes": "Mercedes-Benz", "merc": "Mercedes-Benz",
            "vw": "Volkswagen", "volks": "Volkswagen", "bimmer": "BMW", "beamer": "BMW",
            "vovo": "Volvo", "toy": "Toyota", "peug": "Peugeot", "pug": "Peugeot", "reno": "Renault",
            "chev": "Chevrolet", "citro": "Citroën", "alfa": "Alfa Romeo"
        }
        for alias, real_brand in aliases.items():
            if re.search(rf'\b{alias}\b', text_lower):
                entities['brand'] = real_brand
                text_lower = text_lower.replace(alias, ' ')
                break
                
    # 3.5 Extract Model (Flexible Matching)
    # We clean the text to focus on the model part
    clean_text = re.sub(r'\s+', ' ', text_lower).strip()
    
    if available_models and len(clean_text) > 2:
        # Strategy: find titles that contain the user's keywords
        # or find if the clean_text is a substring of a known model
        sorted_models = sorted([str(m) for m in available_models if str(m) != 'nan' and len(str(m)) > 2], key=len, reverse=True)
        
        # 1st pass: exact match within title
        for model in sorted_models:
            model_low = model.lower()
            if clean_text in model_low:
                entities['model'] = model
                break
                
        # 2nd pass: token overlap (if no exact substring match)
        if not entities['model']:
            query_tokens = set(clean_text.split())
            if query_tokens:
                best_model = None
                max_overlap = 0
                for model in sorted_models:
                    model_tokens = set(model.lower().split())
                    overlap = len(query_tokens.intersection(model_tokens))
                    if overlap > max_overlap:
                        max_overlap = overlap
                        best_model = model
                
                # Threshold for matching: at least 50% of query tokens must match or at least 1 significant token
                if max_overlap >= 1:
                    entities['model'] = best_model

    # 3.7 Extract Location
    if available_locations:
        sorted_locs = sorted([str(l) for l in available_locations if str(l) != 'nan'], key=len, reverse=True)
        for loc in sorted_locs:
            if loc.lower() in text_lower:
                entities['location'] = loc
                break

    return entities
            
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
