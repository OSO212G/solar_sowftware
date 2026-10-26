"""Geocoding helper using Nominatim (OpenStreetMap) and OpenTopoData."""
import requests


def geocode_address(query: str):
    """Return (lat, lon, display_name) for an address query, or None on failure."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
    }
    headers = {
        "User-Agent": "Suria/0.1.0 (solar pre-feasibility tool)",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        result = data[0]
        return float(result["lat"]), float(result["lon"]), result.get("display_name", query)
    except Exception:
        return None


def lookup_altitude(lat: float, lon: float):
    """Return altitude in metres from OpenTopoData SRTM, or None on failure."""
    url = "https://api.opentopodata.org/v1/srtm90m"
    params = {"locations": f"{lat},{lon}"}
    headers = {"User-Agent": "Suria/0.1.0"}
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if results:
            elevation = results[0].get("elevation")
            if elevation is not None:
                return round(elevation)
    except Exception:
        pass
    return None
