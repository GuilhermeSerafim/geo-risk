from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from shapely.ops import transform as shp_transform, nearest_points
from pyproj import Transformer
import json
import numpy as np

gj = json.load(open("data/exportCurtibaTypeAllRivers.geojson", encoding="utf-8"))
features = gj["features"]
water_geoms = [shape(f["geometry"]) for f in features]
tree = STRtree(water_geoms)

def utm_transformer(lon, lat):
    zone = int((lon + 180)//6) + 1
    epsg = 32700 + zone
    return Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)

def distance_to_water_info(lon, lat):
    pt = Point(lon, lat)
    nearest_obj = tree.nearest(pt)

    if isinstance(nearest_obj, (int, np.integer)):
        idx = int(nearest_obj)
        nearest_geom = water_geoms[idx]
    else:
        nearest_geom = nearest_obj
        idx = water_geoms.index(nearest_geom)

    tr = utm_transformer(lon, lat)
    pt_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), pt)
    geom_m = shp_transform(lambda x,y,z=None: tr.transform(x,y), nearest_geom)

    p_user_m, p_rio_m = nearest_points(pt_m, geom_m)
    dist_m = p_user_m.distance(p_rio_m)

    tr_inv = Transformer.from_crs(tr.target_crs, "EPSG:4326", always_xy=True)
    rx, ry = tr_inv.transform(p_rio_m.x, p_rio_m.y)

    return dist_m, idx, (rx, ry)
