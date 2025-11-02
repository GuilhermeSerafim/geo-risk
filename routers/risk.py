from fastapi import APIRouter
from pydantic import BaseModel
from shapely.geometry import shape
from services.water_service import distance_to_water_info, features
from services.elevation_service import elevation_m

router = APIRouter()

class DistanceReq(BaseModel):
    polygon: dict

@router.post("/risk")
def risk_api(req: DistanceReq):
    geom = shape(req.polygon.get("geometry", req.polygon))
    rep = geom.representative_point()
    lon, lat = rep.x, rep.y

    dist_m, idx, (rio_lon, rio_lat) = distance_to_water_info(lon, lat)
    rio_feature = features[idx]
    rio_nome = rio_feature["properties"].get("name", "Desconhecido")

    elev_ponto = elevation_m(lat, lon)
    elev_rio = elevation_m(rio_lat, rio_lon)
    queda_rel = (elev_ponto - elev_rio) if elev_ponto and elev_rio else None

    if dist_m < 150 and (queda_rel is not None and queda_rel < 5):
        score, nivel = 9.0, "Alto"
    elif dist_m < 300 or (queda_rel is not None and queda_rel < 10):
        score, nivel = 6.0, "Médio"
    else:
        score, nivel = 2.0, "Baixo"

    return {
        "score": score,
        "nivel": nivel,
        "distancia_rio_m": round(dist_m, 1),
        "queda_relativa_m": round(queda_rel, 1) if queda_rel is not None else None,
        "rio_mais_proximo": rio_nome
    }
