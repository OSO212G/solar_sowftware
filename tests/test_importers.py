"""Tests for KML and GeoJSON importers."""
import json
from pathlib import Path

import pytest

from suria.importers import import_kml, import_geojson


def test_import_geojson_polygon(tmp_path):
    data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Rooftop A"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [101.69, 3.14],
                            [101.691, 3.14],
                            [101.691, 3.141],
                            [101.69, 3.141],
                            [101.69, 3.14],
                        ]
                    ],
                },
            }
        ],
    }
    p = tmp_path / "test.geojson"
    p.write_text(json.dumps(data))
    result = import_geojson(p)
    assert len(result) == 1
    assert result[0]["name"] == "Rooftop A"
    assert len(result[0]["coords"]) == 5
    assert result[0]["coords"][0] == [101.69, 3.14]


def test_import_geojson_multipolygon(tmp_path):
    data = {
        "type": "Feature",
        "properties": {"name": "Site"},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [
                [
                    [
                        [101.0, 3.0],
                        [101.1, 3.0],
                        [101.1, 3.1],
                        [101.0, 3.1],
                        [101.0, 3.0],
                    ]
                ],
                [
                    [
                        [102.0, 4.0],
                        [102.1, 4.0],
                        [102.1, 4.1],
                        [102.0, 4.1],
                        [102.0, 4.0],
                    ]
                ],
            ],
        },
    }
    p = tmp_path / "test.geojson"
    p.write_text(json.dumps(data))
    result = import_geojson(p)
    assert len(result) == 2
    assert result[0]["name"] == "Site"
    assert result[1]["name"] == "Site"


def test_import_geojson_closes_ring(tmp_path):
    data = {
        "type": "Polygon",
        "coordinates": [
            [
                [101.0, 3.0],
                [101.1, 3.0],
                [101.1, 3.1],
                [101.0, 3.1],
            ]
        ],
    }
    p = tmp_path / "test.geojson"
    p.write_text(json.dumps(data))
    result = import_geojson(p)
    assert len(result) == 1
    assert result[0]["coords"][0] == result[0]["coords"][-1]


def test_import_kml(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <name>Rooftop B</name>
          <Polygon>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>
                  101.69,3.14,0
                  101.691,3.14,0
                  101.691,3.141,0
                  101.69,3.141,0
                  101.69,3.14,0
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>
        </Placemark>
      </Document>
    </kml>
    """
    p = tmp_path / "test.kml"
    p.write_text(kml)
    result = import_kml(p)
    assert len(result) == 1
    assert result[0]["name"] == "Rooftop B"
    assert len(result[0]["coords"]) == 5
    assert result[0]["coords"][0] == [101.69, 3.14]


def test_import_kml_without_name(tmp_path):
    kml = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <Polygon>
            <outerBoundaryIs>
              <LinearRing>
                <coordinates>
                  101.0,3.0,0 101.1,3.0,0 101.1,3.1,0 101.0,3.1,0 101.0,3.0,0
                </coordinates>
              </LinearRing>
            </outerBoundaryIs>
          </Polygon>
        </Placemark>
      </Document>
    </kml>
    """
    p = tmp_path / "test.kml"
    p.write_text(kml)
    result = import_kml(p)
    assert len(result) == 1
    assert result[0]["name"] == "Imported"
