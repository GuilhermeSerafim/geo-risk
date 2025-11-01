from fastapi import FastAPI
from pydantic import BaseModel
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.ops import transform as shp_transform
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

def distance_to_water_m(lon, lat):
    pt = Point(lon, lat)
    nearest_idx = tree.nearest(pt)  # pode retornar índice ou geometria, dependendo da versão

    # normaliza para índice
    import numpy as np
    if not isinstance(nearest_idx, (int, np.integer)):
        nearest_idx = water_geoms.index(nearest_idx)

    nearest_geom = water_geoms[nearest_idx]
    tr = utm_transformer(lon, lat)
    pt_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), pt)
    nearest_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), nearest_geom)
    dist_m = pt_m.distance(nearest_m)

    return dist_m, nearest_idx

# 4) Payload de entrada (polígono GeoJSON)
class DistanceReq(BaseModel):
    polygon: dict  # GeoJSON geometry ou feature

@app.post("/distance")
def distance_api(req: DistanceReq):
    geom = shape(req.polygon.get("geometry", req.polygon))
    rep = geom.representative_point()
    lon, lat = rep.x, rep.y

    dist_m, nearest_idx = distance_to_water_m(lon, lat)
    rio_feature = features[nearest_idx]
    rio_nome = rio_feature["properties"].get("name", "Desconhecido")

    return {
        "distancia_rio_m": round(dist_m, 1),
        "rio_mais_proximo": rio_nome
    }
