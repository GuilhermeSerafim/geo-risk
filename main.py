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
gj = json.load(open("data/export.geojson", encoding="utf-8"))
water_geoms = []
for f in gj["features"]:
    g = shape(f["geometry"])
    if g.geom_type.startswith("Polygon"):
        g = g.boundary
    water_geoms.append(g)

# 2) Índice espacial (vizinho mais próximo)
tree = STRtree(water_geoms)

# 3) Utilitários de projeção (lon/lat -> metros UTM)
def utm_transformer(lon, lat):
    # zona UTM aproximada a partir da longitude
    zone = int((lon + 180)//6) + 1
    epsg = 32700 + zone  # SIRGAS/UTM Hemisfério Sul
    return Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)

def distance_to_water_m(lon, lat):
    pt = Point(lon, lat)
    nearest = tree.nearest(pt)
    tr = utm_transformer(lon, lat)
    pt_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), pt)
    nearest_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), nearest)
    return pt_m.distance(nearest_m)

# 4) Payload de entrada (polígono GeoJSON)
class DistanceReq(BaseModel):
    polygon: dict  # GeoJSON geometry ou feature

@app.post("/distance")
def distance_api(req: DistanceReq):
    geom = shape(req.polygon.get("geometry", req.polygon))
    rep = geom.representative_point()  # ponto representativo da área
    lon, lat = rep.x, rep.y
    dist_m = distance_to_water_m(lon, lat)
    return {"distancia_rio_m": round(dist_m, 1)}
