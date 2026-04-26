def weathercode_is_precip(code):
    # Open-Meteo weather codes indicating precipitation or showers
    precip_codes = set([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 71, 73, 75, 77, 80, 81, 82, 85, 86, 95, 96, 99])
    try:
        return int(code) in precip_codes
    except Exception:
        return False


def recommend_outfit(temp_c, weather_code=None, sex='other', age=None, occasion='Casual'):
    # Basic layered recommendation heuristic
    layers = 1
    desc = []

    if temp_c is None:
        raise ValueError('temp_c required')

    # Determine base layers from temperature
    if temp_c >= 25:
        layers = 0
        desc.append('Light clothing (t-shirt/shorts or single layer)')
    elif 15 <= temp_c < 25:
        layers = 1
        desc.append('Light layer (long-sleeve or light jacket)')
    elif 5 <= temp_c < 15:
        layers = 2
        desc.append('Moderate layers (shirt + sweater/jacket)')
    else:  # temp_c < 5
        layers = 3
        desc.append('Warm layers (thermal + sweater + coat)')

    # Adjust for precipitation
    precip = weathercode_is_precip(weather_code) if weather_code is not None else False
    if precip:
        desc.append('Waterproof outerwear recommended (raincoat/umbrella)')

    # Adjust for age (older people often need more layers)
    if age is not None:
        try:
            age = int(age)
            if age >= 65 and layers > 0:
                layers += 1
                desc.append('Add an extra warm layer for older adults')
        except Exception:
            pass

    # Slight sex-based adjustment (optional and mild)
    if sex and sex.lower() in ('female', 'f'):
        # some style preference: suggest one stylish outer layer
        desc.append('Consider a stylish layer (blazer/cardigan) based on occasion')

    # Occasion affects suggested outfit type
    occ = occasion.lower() if occasion else 'casual'
    outfit_type = 'Casual'
    if 'formal' in occ or 'business' in occ:
        outfit_type = 'Formal / Business'
        desc.append('Prefer tailored pieces (shirt, blazer, dress)')
    elif 'sport' in occ or 'ath' in occ:
        outfit_type = 'Athletic / Sport'
        desc.append('Wear breathable, activewear layers')
    elif 'party' in occ or 'night' in occ:
        outfit_type = 'Party / Night Out'
        desc.append('Consider statement outerwear and smart layers')
    else:
        desc.append('Casual and comfortable clothing')

    # Cap layers to a reasonable range
    layers = max(0, min(layers, 5))

    return {
        'temp_c': temp_c,
        'weather_code': weather_code,
        'layers_recommended': layers,
        'outfit_type': outfit_type,
        'notes': desc
    }
