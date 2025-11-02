import requests

def elevation_m(lat, lon):
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
    r = requests.get(url, timeout=10)
    data = r.json()
    return data["elevation"][0] if "elevation" in data else None
