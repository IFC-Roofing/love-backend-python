"""
Address helpers for DMM: parse from-address JSON, normalize US state.
"""
import json
from typing import Any, Dict, Optional

US_STATE_TO_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "district of columbia": "DC", "florida": "FL", "georgia": "GA", "hawaii": "HI",
    "idaho": "ID", "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY",
}


def normalize_state(state: Optional[str]) -> Optional[str]:
    if not state or not state.strip():
        return state
    s = state.strip()
    if len(s) <= 2:
        return s.upper()
    return US_STATE_TO_ABBR.get(s.lower(), state)


def parse_address_json(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    """Parse DMM_FROM_ADDRESS or DMM_SENDER_COPY_ADDRESS JSON."""
    if not raw or not raw.strip():
        return None
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        street = data.get("street") or data.get("address_line1") or ""
        city = data.get("city") or ""
        state = normalize_state(data.get("state"))
        postal = str(data.get("postal_code") or data.get("zip") or "").strip()
        country = (data.get("country") or "US").strip() or "US"
        return {
            "first_name": data.get("first_name") or "",
            "last_name": data.get("last_name") or "",
            "company": data.get("company") or "",
            "address_line1": street,
            "address_city": city,
            "address_state": state or "",
            "address_zip": postal,
            "address_country": country,
        }
    except (json.JSONDecodeError, TypeError):
        return None
