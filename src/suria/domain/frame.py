"""Cartesian frame utilities — convert between lat/lon and local metres."""
from __future__ import annotations

import math
from functools import lru_cache
from typing import List, Tuple

import pyproj
from shapely.geometry import Polygon
from shapely.ops import transform as shapely_transform

from suria.domain import CartesianFrame


def _utm_epsg(lat: float, lon: float) -> int:
    """Return the UTM EPSG code for a lat/lon pair."""
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone if lat >= 0 else 32700 + zone


def make_frame(lat: float, lon: float, rotation_deg: float = 0.0) -> CartesianFrame:
    """Create a frozen CartesianFrame from a site origin."""
    return CartesianFrame(
        origin_lat=lat,
        origin_lon=lon,
        utm_epsg=_utm_epsg(lat, lon),
        rotation_deg=rotation_deg,
    )


@lru_cache(maxsize=16)
def _get_transformer(utm_epsg: int) -> pyproj.Transformer:
    """Cached pyproj transformer for a given UTM zone."""
    return pyproj.Transformer.from_crs("EPSG:4326", f"EPSG:{utm_epsg}", always_xy=True)


@lru_cache(maxsize=16)
def _get_inverse_transformer(utm_epsg: int) -> pyproj.Transformer:
    """Cached inverse pyproj transformer for a given UTM zone."""
    return pyproj.Transformer.from_crs(f"EPSG:{utm_epsg}", "EPSG:4326", always_xy=True)


def to_xy(frame: CartesianFrame, lon: float, lat: float) -> Tuple[float, float]:
    """Convert lat/lon to frame-local metres."""
    transformer = _get_transformer(frame.utm_epsg)
    x, y = transformer.transform(lon, lat)
    if frame.rotation_deg != 0:
        rad = math.radians(frame.rotation_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        ox, oy = transformer.transform(frame.origin_lon, frame.origin_lat)
        dx = x - ox
        dy = y - oy
        x = ox + dx * cos_r - dy * sin_r
        y = oy + dx * sin_r + dy * cos_r
    return x, y


def to_latlon(frame: CartesianFrame, x: float, y: float) -> Tuple[float, float]:
    """Convert frame-local metres back to lat/lon."""
    if frame.rotation_deg != 0:
        rad = math.radians(-frame.rotation_deg)
        cos_r = math.cos(rad)
        sin_r = math.sin(rad)
        transformer = _get_transformer(frame.utm_epsg)
        ox, oy = transformer.transform(frame.origin_lon, frame.origin_lat)
        dx = x - ox
        dy = y - oy
        x = ox + dx * cos_r - dy * sin_r
        y = oy + dx * sin_r + dy * cos_r
    inverse = _get_inverse_transformer(frame.utm_epsg)
    lon, lat = inverse.transform(x, y)
    return lon, lat


def polygon_to_xy(frame: CartesianFrame, coords: List[List[float]]) -> List[Tuple[float, float]]:
    """Convert a GeoJSON [lon, lat] polygon to frame-local xy metres."""
    return [to_xy(frame, c[0], c[1]) for c in coords]


def polygon_to_latlon(frame: CartesianFrame, coords: List[Tuple[float, float]]) -> List[List[float]]:
    """Convert a frame-local xy polygon back to GeoJSON [lon, lat]."""
    return [[lon, lat] for lon, lat in (to_latlon(frame, x, y) for x, y in coords)]
