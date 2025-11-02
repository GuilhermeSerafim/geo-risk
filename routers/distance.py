from fastapi import APIRouter
from pydantic import BaseModel
from shapely.geometry import shape
from services.water_service import distance_to_water_info, features

router = APIRouter()

class DistanceReq(BaseModel):
    polygon: dict

@router.post("/distance")
def distance_api(req: DistanceReq):
    geom = shape(req.polygon.get("geometry", req.polygon))
    rep = geom.representative_point()
    lon, lat = rep.x, rep.y

    dist_m, nearest_idx, (rio_lon, rio_lat) = distance_to_water_info(lon, lat)
    rio_feature = features[nearest_idx]
    props = rio_feature.get("properties", {})
    rio_nome = props.get("name", "Desconhecido")
    rio_tipo = props.get("waterway", "desconhecido")

    return {
        "distancia_rio_m": round(dist_m, 1),
        "rio_mais_proximo": rio_nome,
        "waterway": rio_tipo,
        "nearest_point": {"lon": rio_lon, "lat": rio_lat}
    }
