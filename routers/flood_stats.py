from fastapi import APIRouter
from pydantic import BaseModel
from shapely.geometry import shape
from typing import Optional
from services.elevation_service import mean_hand_within, coverage_pct_within

router = APIRouter()

class FloodStatsReq(BaseModel):
    # prefer lat/lon
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    polygon: Optional[dict] = None
    radius_m: float = 200.0
    hand_band: int = 1
    coverage_band: int = 1


@router.post("/flood-stats")
def flood_stats_api(req: FloodStatsReq):
    if req.latitude is not None and req.longitude is not None:
        lat, lon = req.latitude, req.longitude
    elif req.polygon:
        geom = shape(req.polygon.get("geometry", req.polygon))
        rep = geom.representative_point()
        lon, lat = rep.x, rep.y
    else:
        return {"error": "Provide latitude/longitude or polygon GeoJSON."}

    hand_mean = None
    cov_pct = None

    # fixed paths (data files in repo)
    hand_path = "data/2024_urban_height_above_nearest_drainage_1-1-1_08814634-6bf1-40b4-a3f1-ca3f1dc98400.tif"
    coverage_path = "data/2023_coverage_coverage_10m_1-91-51_8884c309-3a9c-4619-8054-8cf1432fcf06.tif"
    coverage_value = 24

    try:
        hand_mean = mean_hand_within(hand_path, lat, lon, req.radius_m, band=req.hand_band)
    except Exception:
        hand_mean = None

    try:
        cov_pct = coverage_pct_within(coverage_path, lat, lon, req.radius_m, target_value=coverage_value, band=req.coverage_band)
    except Exception:
        cov_pct = None

    return {
        "mean_hand_m": hand_mean,
        "coverage_pct": cov_pct,
        "query_point": {"lon": lon, "lat": lat}
    }
