def immoscount24_url_generator(zip: list, min_rooms: float) -> str:
    """Generate URL for immo website"""
    base_url = "https://www.immoscout24.ch/en"
    url = f"{base_url}/flat/rent/postcode-{zip[0]}?nrf={min_rooms}"
    if len(zip) == 2:
        url = f"{base_url}/flat/rent/postcode-{zip[0]}?loc=geo-zipcode-{zip[1]}&nrf={min_rooms}"

    if len(zip) > 2:
        for z in zip[1:]:
            url += f"%2Cgeo-zipcode-{z}"
        url += f"&nrf={min_rooms}"

    return url

def homegate24_url_generator(zip: list, min_rooms: float) -> str:
    # https://www.homegate.ch/mieten/wohnung/plz-3007/trefferliste?ac=4.5&o=dateCreated-desc&loc=geo-zipcode-3008%2Cgeo-zipcode-3011
    base_url = "https://www.homegate.ch/mieten/wohnung/"
    url = f"{base_url}plz-{zip[0]}/trefferliste?ac={min_rooms}"
    if len(zip) == 2:
        url = f"{base_url}plz-{zip[0]}/trefferliste?ac={min_rooms}&loc=geo-zipcode-{zip[1]}"
    if len(zip) > 2:
        for z in zip[1:]:
            url += f"%2Cgeo-zipcode-{z}"
        url += f"&ac={min_rooms}"

    return url