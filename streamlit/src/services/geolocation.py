from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st


@st.cache_data(ttl=3600)
def reverse_geocode_region(latitude: float, longitude: float) -> str:
    params = urlencode(
        {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "accept-language": "ko",
        }
    )
    request = Request(
        f"https://nominatim.openstreetmap.org/reverse?{params}",
        headers={"User-Agent": "SKN28-Streamlit-Legal-Assistant/0.1"},
    )
    with urlopen(request, timeout=5) as response:
        payload = json.loads(response.read().decode("utf-8"))

    address = payload.get("address", {})
    city = (
        address.get("city")
        or address.get("municipality")
        or address.get("province")
        or address.get("state")
    )
    district = address.get("borough") or address.get("city_district") or address.get("county")

    if city and district:
        return f"{city} {district}"
    return city or district or ""
