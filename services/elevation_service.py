import requests
from . import flood_stats


def elevation_m(lat, lon):
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
    r = requests.get(url, timeout=10)
    data = r.json()
    return data["elevation"][0] if "elevation" in data else None


def mean_hand_within(path, lat, lon, r_m, band=1):
    """Wrapper to compute mean HAND within radius using flood_stats.mean_within_radius.

    path: path to HAND raster
    lat, lon: point in degrees
    r_m: radius in meters
    """
    return flood_stats.mean_within_radius(path, lat, lon, r_m, band=band)


def coverage_pct_within(path, lat, lon, r_m, target_value=24, band=1):
    """Wrapper to compute percentage of coverage equal to target_value within radius.
    """
    return flood_stats.percentage_equal_value_within_radius(path, lat, lon, r_m, target_value=target_value, band=band)
