from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from services.water_service import areas_rosa_within

router = APIRouter()

class AreasRosaReq(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_m: float = 200.0


@router.post("/areas-rosa")
def areas_rosa_api(req: AreasRosaReq):
    if req.latitude is None or req.longitude is None:
        return {"error": "Provide latitude and longitude."}

    matches = areas_rosa_within(req.longitude, req.latitude, req.radius_m)
    return {"count": len(matches), "matches": matches}
