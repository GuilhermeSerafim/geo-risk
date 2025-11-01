from fastapi import FastAPI
from pydantic import BaseModel
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.ops import transform as shp_transform, nearest_points
from pyproj import Transformer
import json

app = FastAPI()

# adicione isto após app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ajuste depois
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 1) Carregar rios de Pinheiros (se tiver Polygon, vira linha/contorno)
gj = json.load(open("data/exportCuritiba.geojson", encoding="utf-8"))
features = gj["features"]
water_geoms = [shape(f["geometry"]) for f in features]
tree = STRtree(water_geoms)


# 3) Utilitários de projeção (lon/lat -> metros UTM)
def utm_transformer(lon, lat):
    # zona UTM aproximada a partir da longitude
    zone = int((lon + 180)//6) + 1
    epsg = 32700 + zone  # SIRGAS/UTM Hemisfério Sul
    return Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)

def distance_to_water_info(lon, lat):
    pt = Point(lon, lat)
    nearest_obj = tree.nearest(pt)

    import numpy as np
    if isinstance(nearest_obj, (int, np.integer)):
        idx = int(nearest_obj)
        nearest_geom = water_geoms[idx]
    else:
        nearest_geom = nearest_obj
        idx = water_geoms.index(nearest_geom)

    # Projeção p/ metros
    tr = utm_transformer(lon, lat)
    pt_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), pt)
    geom_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), nearest_geom)

    # Ponto exato no rio mais próximo (em metros)
    p_user_m, p_rio_m = nearest_points(pt_m, geom_m)
    dist_m = p_user_m.distance(p_rio_m)

    # Volta o ponto do rio para WGS84
    tr_inv = Transformer.from_crs(tr.target_crs, "EPSG:4326", always_xy=True)
    rx, ry = tr_inv.transform(p_rio_m.x, p_rio_m.y)

    return dist_m, idx, (rx, ry)

# 4) Payload de entrada (polígono GeoJSON)
class DistanceReq(BaseModel):
    polygon: dict  # GeoJSON geometry ou feature

@app.post("/distance")
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
