from fastapi import APIRouter
from pydantic import BaseModel
from shapely.geometry import shape
from services.water_service import distance_to_water_info, features
from services.elevation_service import elevation_m
from services.ai_service import get_ai_assessment

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

    # 🧠 Pergunta contextual para a IA
    queda_rel_str = f"{queda_rel:.1f}" if queda_rel is not None else "N/A"
    prompt = (
        f"Com base nas seguintes informações:\n"
        f"- Distância até o rio: {dist_m:.1f} metros\n"
        f"- Queda relativa (diferença de altitude): {queda_rel_str} metros\n"
        f"- Rio mais próximo: {rio_nome}\n\n"
        "Classifique o risco de alagamento como **Baixo**, **Médio** ou **Alto**, "
        "e explique brevemente o motivo da classificação de forma técnica e objetiva."
    )
    
    ai = get_ai_assessment(prompt)

    return {
        "distancia_rio_m": round(dist_m, 1),
        "queda_relativa_m": round(queda_rel, 1) if queda_rel is not None else None,
        "rio_mais_proximo": rio_nome,
        "resposta_ia": ai.explanation,
        "risk_level": ai.risk_level
    }
