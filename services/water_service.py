# from shapely.geometry import shape, Point
# from shapely.strtree import STRtree
# from shapely.ops import transform as shp_transform, nearest_points
# from pyproj import Transformer
# import json
# import numpy as np

# gj = json.load(open("data/exportCuritiba.geojson", encoding="utf-8"))
# features = gj["features"]
# water_geoms = [shape(f["geometry"]) for f in features]
# tree = STRtree(water_geoms)

# def utm_transformer(lon, lat):
#     zone = int((lon + 180)//6) + 1
#     epsg = 32700 + zone
#     return Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)

# def distance_to_water_info(lon, lat):
#     pt = Point(lon, lat)
#     nearest_obj = tree.nearest(pt)

#     if isinstance(nearest_obj, (int, np.integer)):
#         idx = int(nearest_obj)
#         nearest_geom = water_geoms[idx]
#     else:
#         nearest_geom = nearest_obj
#         idx = water_geoms.index(nearest_geom)

#     tr = utm_transformer(lon, lat)
#     pt_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), pt)
#     geom_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), nearest_geom)

#     p_user_m, p_rio_m = nearest_points(pt_m, geom_m)
#     dist_m = p_user_m.distance(p_rio_m)

#     tr_inv = Transformer.from_crs(tr.target_crs, "EPSG:4326", always_xy=True)
#     rx, ry = tr_inv.transform(p_rio_m.x, p_rio_m.y)

#     return dist_m, idx, (rx, ry)

from shapely.geometry import shape, Point, Polygon, MultiPolygon, LineString
from shapely.strtree import STRtree
from shapely.ops import transform as shp_transform, nearest_points
import json
import math
import numpy as np

# ---- Carrega geometrias de água e constrói o índice espacial ----
gj = json.load(open("data/exportCuritiba.geojson", encoding="utf-8"))
features = gj["features"]
water_geoms = [shape(f["geometry"]) for f in features]
tree = STRtree(water_geoms)

# ---- Carrega áreas rosa (historico de alagamento) ----
try:
    areas_gj = json.load(open("data/areas_rosa_curitiba.geojson", encoding="utf-8"))
    areas_rosa_features = areas_gj.get("features", [])
    areas_rosa_geoms = [shape(f.get("geometry")) for f in areas_rosa_features]
    areas_rosa_tree = STRtree(areas_rosa_geoms) if areas_rosa_geoms else None
except Exception:
    areas_rosa_features = []
    areas_rosa_geoms = []
    areas_rosa_tree = None

# ---- Util: metros por grau na latitude de referência ----
def _meters_per_deg(lat_deg: float):
    lat_rad = math.radians(lat_deg)
    m_per_deg_lat = 111_320.0                    # ~constante
    m_per_deg_lon = 111_320.0 * max(math.cos(lat_rad), 1e-9)  # evita 0 perto dos polos
    return m_per_deg_lon, m_per_deg_lat

# ---- Projeção local (equiretangular) centrada no ponto (lon0, lat0) ----
def _make_local_transforms(lon0: float, lat0: float):
    mx, my = _meters_per_deg(lat0)

    def fwd(x, y, z=None):
        # (lon, lat) -> (x_m, y_m) em metros, com origem no ponto do usuário
        return ( (x - lon0) * mx, (y - lat0) * my )

    def inv(xm, ym, z=None):
        # (x_m, y_m) -> (lon, lat)
        return ( xm / mx + lon0, ym / my + lat0 )

    return fwd, inv

def distance_to_water_info(lon: float, lat: float):
    """
    Retorna:
      - dist_m: distância em metros do ponto (lon,lat) até a geometria d'água mais próxima
      - idx: índice da feição escolhida em 'water_geoms'
      - (rx, ry): coordenadas lon/lat do ponto mais próximo SOBRE a geometria d'água
    Sem usar pyproj.
    """
    pt = Point(lon, lat)

    # 1) Busca candidato mais próximo via STRtree (em graus) — rápido
    nearest_obj = tree.nearest(pt)
    if isinstance(nearest_obj, (int, np.integer)):
        idx = int(nearest_obj)
        nearest_geom = water_geoms[idx]
    else:
        nearest_geom = nearest_obj
        # cuidado: .index() é O(n); se performance virar problema, armazene um mapa geom->idx
        idx = water_geoms.index(nearest_geom)

    # 2) Constrói projeção local em metros centrada no ponto do usuário
    fwd, inv = _make_local_transforms(lon, lat)

    # 3) Projeta para o plano local (metros)
    pt_m = shp_transform(fwd, pt)                  # deve virar (0,0)
    geom_m = shp_transform(fwd, nearest_geom)

    # 4) Ponto mais próximo e distância em metros
    p_user_m, p_rio_m = nearest_points(pt_m, geom_m)
    dist_m = p_user_m.distance(p_rio_m)            # Euclidiana já em metros

    # 5) Converte de volta o ponto sobre o rio para lon/lat
    rx, ry = inv(p_rio_m.x, p_rio_m.y)

    return dist_m, idx, (rx, ry)


def areas_rosa_within(lon: float, lat: float, r_m: float):
    """
    Retorna lista de feições 'rosa' que intersectam o círculo de raio r_m (metros)
    centrado em (lon, lat). Para eficiência, usa projeção local em metros.

    Cada item retornado é um dict: {"index": int, "properties": ..., "distance_m": float, "geometry": geojson_geom}
    """
    if not areas_rosa_tree:
        return []

    # projeção local
    fwd, inv = _make_local_transforms(lon, lat)
    pt_m = shp_transform(fwd, Point(lon, lat))

    # criar buffer em metros no plano local
    buffer_m = pt_m.buffer(r_m)

    # candidates: query tree with bbox around buffer (transform bbox back to degrees)
    minx_m, miny_m, maxx_m, maxy_m = buffer_m.bounds
    minlon, minlat = inv(minx_m, miny_m)
    maxlon, maxlat = inv(maxx_m, maxy_m)

    # construir uma bbox polygon em graus para filtrar
    bbox = Polygon([(minlon, minlat), (minlon, maxlat), (maxlon, maxlat), (maxlon, minlat)])

    # busca candidatos pela árvore (em graus) - usamos bbox centroid para procurar próximos
    candidates = areas_rosa_tree.query(bbox)

    results = []
    for geom in candidates:
        try:
            # calc dist em metros usando projeção local
            geom_m = shp_transform(fwd, geom)
            p_user_m, p_feat_m = nearest_points(pt_m, geom_m)
            d = p_user_m.distance(p_feat_m)
            if d <= r_m:
                idx = areas_rosa_geoms.index(geom)
                feat = areas_rosa_features[idx]
                results.append({
                    "index": idx,
                    "properties": feat.get("properties", {}),
                    "distance_m": float(d),
                    "geometry": feat.get("geometry")
                })
        except Exception:
            continue

    return results
