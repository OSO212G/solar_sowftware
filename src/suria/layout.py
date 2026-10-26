"""Panel layout engine — polygon packing with setbacks, spacing, and azimuth rotation."""
import math
from typing import List, Optional, Tuple

from shapely.geometry import Polygon, Point

from suria.domain.frame import make_frame, to_xy, to_latlon
from suria.domain import CartesianFrame


def _rotate_point(px, py, cx, cy, cos_r, sin_r):
    """Rotate a point (px, py) around center (cx, cy)."""
    rx = cx + (px - cx) * cos_r - (py - cy) * sin_r
    ry = cy + (px - cx) * sin_r + (py - cy) * cos_r
    return rx, ry


def estimate_panels_from_polygon(
    coords,
    module_length,
    module_width,
    row_spacing_m,
    setback_m,
    portrait=False,
    azimuth=180,
    keepouts=None,
    frame: CartesianFrame = None,
):
    """Estimate panel count from a lat/lon polygon with grid packing.

    Parameters
    ----------
    portrait : bool
        If True, swap module_length and module_width so the narrow edge
        runs horizontally (landscape → portrait).
    azimuth : int
        Array azimuth in degrees (0 = north, 180 = south). The packing grid
        is rotated so panel rows align with the array's orientation.
    keepouts : list[dict] | None
        Obstruction polygons to exclude. Each dict has a "coords" key with
        GeoJSON [lon, lat] polygon points. Only active keepouts with valid
        coords are applied.
    frame : CartesianFrame | None
        Frozen local Cartesian frame. If None, one is created from the first
        polygon coordinate.
    """
    if portrait:
        module_length, module_width = module_width, module_length

    if not coords or len(coords) < 3:
        return 0, [], []

    if frame is None:
        frame = make_frame(coords[0][1], coords[0][0])

    # Convert polygon to local meters using the frozen frame
    meter_points = [to_xy(frame, c[0], c[1]) for c in coords]

    # Compute centroid for rotation
    centroid_x = sum(p[0] for p in meter_points) / len(meter_points)
    centroid_y = sum(p[1] for p in meter_points) / len(meter_points)

    # Rotate polygon to align packing grid with panel orientation
    rotation_rad = math.radians(180 - azimuth)
    if rotation_rad != 0:
        cos_r = math.cos(rotation_rad)
        sin_r = math.sin(rotation_rad)
        meter_points = [
            _rotate_point(p[0], p[1], centroid_x, centroid_y, cos_r, sin_r)
            for p in meter_points
        ]

    poly = Polygon(meter_points)

    if not poly.is_valid or poly.area <= 0:
        return 0, [], []

    # Apply setbacks
    if setback_m > 0:
        try:
            poly = poly.buffer(-setback_m)
        except Exception:
            pass

    if not poly.is_valid or poly.area <= 0:
        return 0, [], []

    # Build rotated keepout polygons in meter space
    keepout_polys = []
    if keepouts:
        for ko in keepouts:
            if not ko.get("active", True):
                continue
            ko_coords = ko.get("coords")
            if not ko_coords or len(ko_coords) < 3:
                continue
            ko_meters = [to_xy(frame, c[0], c[1]) for c in ko_coords]
            if rotation_rad != 0:
                ko_meters = [
                    _rotate_point(p[0], p[1], centroid_x, centroid_y, cos_r, sin_r)
                    for p in ko_meters
                ]
            ko_poly = Polygon(ko_meters)
            if ko_poly.is_valid and ko_poly.area > 0:
                keepout_polys.append(ko_poly)

    # Grid packing
    minx, miny, maxx, maxy = poly.bounds
    panel_count = 0
    panel_centers_m = []
    panel_rectangles_m = []
    half_l = module_length / 2
    half_w = module_width / 2
    y = miny + module_width / 2
    while y < maxy:
        x = minx + module_length / 2
        while x < maxx:
            p = Point(x, y)
            if poly.contains(p):
                # Exclude panels inside any keepout polygon
                in_keepout = False
                for ko_poly in keepout_polys:
                    if ko_poly.contains(p):
                        in_keepout = True
                        break
                if not in_keepout:
                    panel_count += 1
                    panel_centers_m.append((x, y))
                    corners = [
                        (x - half_l, y - half_w),
                        (x + half_l, y - half_w),
                        (x + half_l, y + half_w),
                        (x - half_l, y + half_w),
                    ]
                    panel_rectangles_m.append(corners)
            x += module_length
        y += row_spacing_m

    # Rotate back to original orientation and convert to lat/lon
    panel_centers = []
    panel_rectangles = []

    if rotation_rad != 0:
        cos_r = math.cos(-rotation_rad)
        sin_r = math.sin(-rotation_rad)
        for cx_m, cy_m in panel_centers_m:
            rx, ry = _rotate_point(cx_m, cy_m, centroid_x, centroid_y, cos_r, sin_r)
            lon, lat = to_latlon(frame, rx, ry)
            panel_centers.append([lon, lat])
        for rect in panel_rectangles_m:
            rotated_rect = []
            for cx_m, cy_m in rect:
                rx, ry = _rotate_point(cx_m, cy_m, centroid_x, centroid_y, cos_r, sin_r)
                lon, lat = to_latlon(frame, rx, ry)
                rotated_rect.append([lon, lat])
            panel_rectangles.append(rotated_rect)
    else:
        for cx_m, cy_m in panel_centers_m:
            lon, lat = to_latlon(frame, cx_m, cy_m)
            panel_centers.append([lon, lat])
        for rect in panel_rectangles_m:
            latlon_rect = []
            for cx_m, cy_m in rect:
                lon, lat = to_latlon(frame, cx_m, cy_m)
                latlon_rect.append([lon, lat])
            panel_rectangles.append(latlon_rect)

    return panel_count, panel_centers, panel_rectangles


def polygon_area_m2(coords, frame: CartesianFrame = None):
    """Return polygon area in square metres (coords are GeoJSON [lon, lat])."""
    if not coords or len(coords) < 3:
        return 0.0
    if frame is None:
        frame = make_frame(coords[0][1], coords[0][0])
    meter_points = [to_xy(frame, c[0], c[1]) for c in coords]
    poly = Polygon(meter_points)
    return poly.area if poly.is_valid else 0.0


def calculate_row_spacing(tilt_deg, panel_height_m, sun_angle_deg=30):
    """Calculate minimum row spacing to avoid shading at winter solstice."""
    tilt_rad = math.radians(tilt_deg)
    sun_rad = math.radians(sun_angle_deg)
    spacing = panel_height_m * math.cos(tilt_rad) / math.tan(sun_rad)
    return max(spacing, panel_height_m * 0.5)
