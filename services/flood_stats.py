"""Raster utilities to compute neighborhood statistics (HAND mean, categorical coverage pct).

This module provides:
- mean_within_radius(path, lat, lon, r_m, band=1)
- percentage_equal_value_within_radius(path, lat, lon, r_m, target_value=24, band=1)

The implementations read a small window around a query point and compute
statistics using an ellipse/circle mask. Depends on rasterio and numpy.
"""
import math
import numpy as np
import rasterio
from rasterio import windows
from rasterio.warp import transform as rio_transform
from rasterio.transform import xy


def _radius_in_crs_units(src, lat_deg, r_m):
    """
    Return (rx, ry) radius in the raster CRS units for x and y directions.
    - If CRS is projected (meters), (rx, ry) = (r_m, r_m).
    - If CRS is geographic (degrees), convert meters → degrees using local scale.
    """
    if not src.crs:
        raise RuntimeError("Raster has no CRS.")

    if src.crs.is_geographic:
        # meters per degree
        lat_rad = math.radians(lat_deg)
        meters_per_deg_lat = 111_320.0       # ~constant
        meters_per_deg_lon = 111_320.0 * math.cos(lat_rad)
        rx = r_m / max(meters_per_deg_lon, 1e-9)
        ry = r_m / meters_per_deg_lat
        return rx, ry
    else:
        # assume meters (projected)
        return float(r_m), float(r_m)


def _window_for_circle(src, x, y, rx, ry):
    """
    Build a read window that bounds an ellipse centered at (x,y) with radii (rx, ry)
    in the raster CRS units.
    """
    minx, maxx = x - rx, x + rx
    miny, maxy = y - ry, y + ry

    # Convert bounding box to row/col
    row_min, col_min = src.index(minx, maxy)  # note y is maxy (north)
    row_max, col_max = src.index(maxx, miny)  # note y is miny (south)

    # Ensure proper ordering and clamp to raster bounds
    r0, r1 = sorted((row_min, row_max))
    c0, c1 = sorted((col_min, col_max))
    r0 = max(0, r0); c0 = max(0, c0)
    r1 = min(src.height, r1 + 1); c1 = min(src.width, c1 + 1)

    return windows.Window.from_slices((r0, r1), (c0, c1))


def _ellipse_mask(src, window, x0, y0, rx, ry):
    """
    Create a boolean mask for pixels whose center lies within the ellipse:
        ((x-x0)/rx)^2 + ((y-y0)/ry)^2 <= 1
    in raster CRS units.
    """
    rows = np.arange(int(window.row_off), int(window.row_off + window.height))
    cols = np.arange(int(window.col_off), int(window.col_off + window.width))
    # pixel centers
    xs, _ = xy(src.transform, rows[0], cols, offset="center")
    _, ys = xy(src.transform, rows, cols[0], offset="center")

    X, Y = np.meshgrid(np.array(xs), np.array(ys))  # shape (h, w)
    # Normalize by radii
    if rx <= 0 or ry <= 0:
        return np.zeros((len(rows), len(cols)), dtype=bool)
    mask = ((X - x0) / rx) ** 2 + ((Y - y0) / ry) ** 2 <= 1.0
    return mask


def mean_within_radius(path, lat, lon, r_m, band=1):
    """
    Mean of raster values within a circle of radius r_m (meters) around (lat, lon).
    Ignores NoData.
    """
    with rasterio.Env(GDAL_CACHEMAX=64):
        with rasterio.open(path) as src:
            # Transform query point to raster CRS
            if src.crs and src.crs.to_string() != "EPSG:4326":
                xs, ys = rio_transform("EPSG:4326", src.crs, [lon], [lat])
                xq, yq = xs[0], ys[0]
            else:
                # raster is already geographic
                xq, yq = lon, lat

            rx, ry = _radius_in_crs_units(src, lat, r_m)
            win = _window_for_circle(src, xq, yq, rx, ry)

            # Read masked array to honor nodata
            arr = src.read(band, window=win, masked=True)

            # Build ellipse mask on this window
            mask = _ellipse_mask(src, win, xq, yq, rx, ry)

            # Apply mask to data (also respect nodata mask)
            if np.ma.is_masked(arr):
                combined_mask = (~mask) | arr.mask
                vals = np.ma.array(arr, mask=combined_mask)
            else:
                vals = np.ma.array(arr, mask=~mask)

            if vals.count() == 0:
                return np.nan
            return float(vals.mean())


def percentage_equal_value_within_radius(path, lat, lon, r_m, target_value=24, band=1):
    """
    Percentage (0–100) of pixels equal to 'target_value' within circle r_m around (lat, lon).
    Ignores NoData. Intended for categorical rasters (e.g., coverage).
    """
    with rasterio.Env(GDAL_CACHEMAX=64):
        with rasterio.open(path) as src:
            if src.crs and src.crs.to_string() != "EPSG:4326":
                xs, ys = rio_transform("EPSG:4326", src.crs, [lon], [lat])
                xq, yq = xs[0], ys[0]
            else:
                xq, yq = lon, lat

            rx, ry = _radius_in_crs_units(src, lat, r_m)
            win = _window_for_circle(src, xq, yq, rx, ry)
            arr = src.read(band, window=win, masked=True)

            mask = _ellipse_mask(src, win, xq, yq, rx, ry)

            if np.ma.is_masked(arr):
                valid_mask = (~arr.mask) & mask
                total = int(valid_mask.sum())
                if total == 0:
                    return np.nan
                equal = int((arr.data[valid_mask] == target_value).sum())
            else:
                valid_mask = mask
                total = int(valid_mask.sum())
                if total == 0:
                    return np.nan
                equal = int((arr[valid_mask] == target_value).sum())

            return 100.0 * equal / total


# --------- Example usage ----------
if __name__ == "__main__":
    lat, lon = -25.340555, -49.263572
    r_m = 200  # radius in meters

    hand_path = "2024_urban_height_above_nearest_drainage_1-1-1_08814634-6bf1-40b4-a3f1-ca3f1dc98400.tif"
    cov_path  = "2023_coverage_coverage_10m_1-91-51_8884c309-3a9c-4619-8054-8cf1432fcf06.tif"

    mean_hand = mean_within_radius(hand_path, lat, lon, r_m, band=1)
    pct_24    = percentage_equal_value_within_radius(cov_path, lat, lon, r_m, target_value=24, band=1)

    print(f"Mean urban height within {r_m} m: {mean_hand}")
    print(f"Coverage==24 within {r_m} m: {pct_24:.2f}%")
"""Utilities to compute local flood-related statistics from rasters.

Functions:
- mean_within_radius(path, lat, lon, r_m, band=1)
- percentage_equal_value_within_radius(path, lat, lon, r_m, target_value=24, band=1)

These work with rasters in either geographic (degrees) or projected CRS.
"""
import math
import numpy as np
import rasterio
from rasterio import windows
from rasterio.warp import transform as rio_transform
from rasterio.transform import xy


def _radius_in_crs_units(src, lat_deg, r_m):
    """Return (rx, ry) radius in the raster CRS units for x and y directions.

    - If CRS is projected (meters), (rx, ry) = (r_m, r_m).
    - If CRS is geographic (degrees), convert meters → degrees using local scale.
    """
    if not src.crs:
        raise RuntimeError("Raster has no CRS.")

    if src.crs.is_geographic:
        # meters per degree
        lat_rad = math.radians(lat_deg)
        meters_per_deg_lat = 111_320.0       # ~constant
        meters_per_deg_lon = 111_320.0 * math.cos(lat_rad)
        rx = r_m / max(meters_per_deg_lon, 1e-9)
        ry = r_m / meters_per_deg_lat
        return rx, ry
    else:
        # assume meters (projected)
        return float(r_m), float(r_m)


def _window_for_circle(src, x, y, rx, ry):
    """Build a read window that bounds an ellipse centered at (x,y) with radii (rx, ry)
    in the raster CRS units.
    """
    minx, maxx = x - rx, x + rx
    miny, maxy = y - ry, y + ry

    # Convert bounding box to row/col
    row_min, col_min = src.index(minx, maxy)  # note y is maxy (north)
    row_max, col_max = src.index(maxx, miny)  # note y is miny (south)

    # Ensure proper ordering and clamp to raster bounds
    r0, r1 = sorted((row_min, row_max))
    c0, c1 = sorted((col_min, col_max))
    r0 = max(0, r0); c0 = max(0, c0)
    r1 = min(src.height, r1 + 1); c1 = min(src.width, c1 + 1)

    return windows.Window.from_slices((r0, r1), (c0, c1))


def _ellipse_mask(src, window, x0, y0, rx, ry):
    """Create a boolean mask for pixels whose center lies within the ellipse:
        ((x-x0)/rx)^2 + ((y-y0)/ry)^2 <= 1
    in raster CRS units.
    """
    rows = np.arange(int(window.row_off), int(window.row_off + window.height))
    cols = np.arange(int(window.col_off), int(window.col_off + window.width))
    # pixel centers
    xs, _ = xy(src.transform, rows[0], cols, offset="center")
    _, ys = xy(src.transform, rows, cols[0], offset="center")

    X, Y = np.meshgrid(np.array(xs), np.array(ys))  # shape (h, w)
    # Normalize by radii
    if rx <= 0 or ry <= 0:
        return np.zeros((len(rows), len(cols)), dtype=bool)
    mask = ((X - x0) / rx) ** 2 + ((Y - y0) / ry) ** 2 <= 1.0
    return mask


def mean_within_radius(path, lat, lon, r_m, band=1):
    """Mean of raster values within a circle of radius r_m (meters) around (lat, lon).
    Ignores NoData.
    """
    with rasterio.Env(GDAL_CACHEMAX=64):
        with rasterio.open(path) as src:
            # Transform query point to raster CRS
            if src.crs and src.crs.to_string() != "EPSG:4326":
                xs, ys = rio_transform("EPSG:4326", src.crs, [lon], [lat])
                xq, yq = xs[0], ys[0]
            else:
                # raster is already geographic
                xq, yq = lon, lat

            rx, ry = _radius_in_crs_units(src, lat, r_m)
            win = _window_for_circle(src, xq, yq, rx, ry)

            # Read masked array to honor nodata
            arr = src.read(band, window=win, masked=True)

            # Build ellipse mask on this window
            mask = _ellipse_mask(src, win, xq, yq, rx, ry)

            # Apply mask to data (also respect nodata mask)
            if np.ma.is_masked(arr):
                combined_mask = (~mask) | arr.mask
                vals = np.ma.array(arr, mask=combined_mask)
            else:
                vals = np.ma.array(arr, mask=~mask)

            if vals.count() == 0:
                return float('nan')
            return float(vals.mean())


def percentage_equal_value_within_radius(path, lat, lon, r_m, target_value=24, band=1):
    """Percentage (0–100) of pixels equal to 'target_value' within circle r_m around (lat, lon).
    Ignores NoData. Intended for categorical rasters (e.g., coverage).
    """
    with rasterio.Env(GDAL_CACHEMAX=64):
        with rasterio.open(path) as src:
            if src.crs and src.crs.to_string() != "EPSG:4326":
                xs, ys = rio_transform("EPSG:4326", src.crs, [lon], [lat])
                xq, yq = xs[0], ys[0]
            else:
                xq, yq = lon, lat

            rx, ry = _radius_in_crs_units(src, lat, r_m)
            win = _window_for_circle(src, xq, yq, rx, ry)
            arr = src.read(band, window=win, masked=True)

            mask = _ellipse_mask(src, win, xq, yq, rx, ry)

            if np.ma.is_masked(arr):
                valid_mask = (~arr.mask) & mask
                total = int(valid_mask.sum())
                if total == 0:
                    return float('nan')
                equal = int((arr.data[valid_mask] == target_value).sum())
            else:
                valid_mask = mask
                total = int(valid_mask.sum())
                if total == 0:
                    return float('nan')
                equal = int((arr[valid_mask] == target_value).sum())

            return 100.0 * equal / total


if __name__ == "__main__":
    # quick demo values (won't run in CI)
    lat, lon = -25.340555, -49.263572
    r_m = 200
    print("Module flood_stats loaded. Use mean_within_radius() and percentage_equal_value_within_radius().")
