from fastapi import APIRouter
from pydantic import BaseModel
from shapely.geometry import shape
from typing import Optional
from services.elevation_service import elevation_m, mean_hand_within

router = APIRouter()

class ElevationReq(BaseModel):
    # Preferred: provide latitude/longitude directly
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Backwards compatible: polygon GeoJSON
    polygon: Optional[dict] = None
    radius_m: float = 200.0
    hand_band: int = 1


@router.post("/elevation")
def elevation_api(req: ElevationReq):
    # prefer lat/lon if provided
    if req.latitude is not None and req.longitude is not None:
        lat, lon = req.latitude, req.longitude
    elif req.polygon:
        geom = shape(req.polygon.get("geometry", req.polygon))
        rep = geom.representative_point()
        lon, lat = rep.x, rep.y
    else:
        return {"error": "Provide latitude/longitude or polygon GeoJSON."}

    elev = elevation_m(lat, lon)

    hand_mean = None
    hand_path = "data/2024_urban_height_above_nearest_drainage_1-1-1_08814634-6bf1-40b4-a3f1-ca3f1dc98400.tif"
    try:
        hand_mean = mean_hand_within(hand_path, lat, lon, req.radius_m, band=req.hand_band)
    except Exception:
        hand_mean = None

    return {
        "elevation_m": elev,
        "mean_hand_m": hand_mean,
        "query_point": {"lon": lon, "lat": lat}
    }
