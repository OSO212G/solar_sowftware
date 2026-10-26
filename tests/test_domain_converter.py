"""Tests for flat dict ↔ domain model converter."""
import pytest

from suria.domain.converter import flat_to_project, project_to_flat


SAMPLE_FLAT = {
    "name": "Test Project",
    "customer": "Acme",
    "designer": "Suria",
    "site": {"lat": 3.14, "lon": 101.69, "altitude": 50},
    "arrays": [
        {
            "name": "Array 1",
            "coords": [
                [101.69, 3.14],
                [101.691, 3.14],
                [101.691, 3.141],
                [101.69, 3.141],
                [101.69, 3.14],
            ],
            "tilt": 10,
            "azimuth": 180,
            "modules_per_string": 20,
            "strings": 2,
            "module": "Aiko 650W",
            "keepouts": [
                {
                    "name": "HVAC",
                    "coords": [
                        [101.6902, 3.1402],
                        [101.6904, 3.1402],
                        [101.6904, 3.1404],
                        [101.6902, 3.1404],
                        [101.6902, 3.1402],
                    ],
                    "height_m": 1.5,
                    "active": True,
                }
            ],
        }
    ],
    "module_specs": {
        "Aiko 650W": {
            "name": "Aiko 650W",
            "p_max": 650,
            "voc": 54.0,
            "vmp": 45.3,
            "isc": 15.06,
            "imp": 14.35,
            "length": 2.382,
            "width": 1.134,
        }
    },
    "inverter_specs": {
        "Huawei 10k": {
            "name": "Huawei 10k",
            "p_aco": 10000,
            "p_dco": 10200,
            "v_dco": 600,
            "vdcmin": 200,
            "vdcmax": 1100,
            "efficiency": 0.984,
        }
    },
}


def test_flat_to_project_basic():
    project = flat_to_project(SAMPLE_FLAT)
    assert project.name == "Test Project"
    assert project.customer == "Acme"
    assert project.site.lat == pytest.approx(3.14)
    assert len(project.designs) == 1
    design = project.designs[0]
    assert len(design.field_segments) == 1
    assert len(design.keepouts) == 1
    assert design.keepouts[0].height_m == 1.5
    assert design.frame is not None


def test_roundtrip_name_and_site():
    project = flat_to_project(SAMPLE_FLAT)
    back = project_to_flat(project)
    assert back["name"] == "Test Project"
    assert back["site"]["lat"] == pytest.approx(3.14)
    assert back["site"]["lon"] == pytest.approx(101.69)


def test_roundtrip_component_library():
    project = flat_to_project(SAMPLE_FLAT)
    back = project_to_flat(project)
    assert "Aiko 650W" in back["module_specs"]
    assert "Huawei 10k" in back["inverter_specs"]
    assert back["module_specs"]["Aiko 650W"]["p_max"] == 650
    assert back["inverter_specs"]["Huawei 10k"]["p_aco"] == 10000


def test_roundtrip_array_coords():
    project = flat_to_project(SAMPLE_FLAT)
    back = project_to_flat(project)
    assert len(back["arrays"]) == 1
    coords = back["arrays"][0]["coords"]
    assert len(coords) == 5
    assert coords[0][0] == pytest.approx(101.69, abs=1e-6)
    assert coords[0][1] == pytest.approx(3.14, abs=1e-6)


def test_empty_arrays():
    flat = {
        "name": "Empty",
        "site": {"lat": 0.0, "lon": 0.0},
        "arrays": [],
        "module_specs": {},
        "inverter_specs": {},
    }
    project = flat_to_project(flat)
    assert len(project.designs[0].field_segments) == 0
    back = project_to_flat(project)
    assert back["arrays"] == []
