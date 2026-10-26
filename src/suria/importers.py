"""Import field segments from KML and GeoJSON files."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple


def _parse_kml_coordinates(coord_text: str) -> List[Tuple[float, float]]:
    """Parse a KML <coordinates> string into [(lon, lat), ...]."""
    coords = []
    for part in coord_text.strip().split():
        vals = part.split(",")
        if len(vals) >= 2:
            lon = float(vals[0])
            lat = float(vals[1])
            coords.append((lon, lat))
    return coords


def import_kml(path: Path) -> List[dict]:
    """Return a list of polygon dicts from a KML file.

    Each dict has {"name": str, "coords": [[lon, lat], ...]}.
    Only Polygon geometries are extracted; MultiGeometry is flattened.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    polygons = []
    for placemark in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        name_elem = placemark.find("kml:name", ns)
        name = name_elem.text if name_elem is not None else "Imported"
        for poly in placemark.iter("{http://www.opengis.net/kml/2.2}Polygon"):
            outer = poly.find("kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", ns)
            if outer is not None and outer.text:
                coords = _parse_kml_coordinates(outer.text)
                if len(coords) >= 3:
                    # Close ring if not closed
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    polygons.append({"name": name, "coords": [[c[0], c[1]] for c in coords]})
    return polygons


def import_geojson(path: Path) -> List[dict]:
    """Return a list of polygon dicts from a GeoJSON file.

    Supports FeatureCollection and single Feature. Only Polygon and
    MultiPolygon geometries are extracted.
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    polygons = []

    def _add_polygon(name, ring):
        if len(ring) >= 3:
            # GeoJSON ring is [lon, lat, ...?]
            coords = [[p[0], p[1]] for p in ring]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            polygons.append({"name": name, "coords": coords})

    def _process_feature(name, geometry):
        if geometry is None:
            return
        geom_type = geometry.get("type")
        if geom_type == "Polygon":
            for ring in geometry.get("coordinates", []):
                _add_polygon(name, ring)
        elif geom_type == "MultiPolygon":
            for poly in geometry.get("coordinates", []):
                for ring in poly:
                    _add_polygon(name, ring)

    if data.get("type") == "FeatureCollection":
        for feat in data.get("features", []):
            props = feat.get("properties", {})
            name = props.get("name", "Imported")
            _process_feature(name, feat.get("geometry"))
    elif data.get("type") == "Feature":
        props = data.get("properties", {})
        name = props.get("name", "Imported")
        _process_feature(name, data.get("geometry"))
    elif data.get("type") in ("Polygon", "MultiPolygon"):
        _process_feature("Imported", data)

    return polygons
