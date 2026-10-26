"""Tests for Pydantic boundary validation."""
import pytest

from suria.domain.simulation_input import SimulationInput, ArrayInput, ModuleInput, InverterInput


def _minimal_project():
    return {
        "name": "Test",
        "site": {"lat": 3.14, "lon": 101.69, "altitude": 50},
        "arrays": [
            {
                "name": "A1",
                "module": "Test Module",
                "inverter": "Test Inverter",
                "tilt": 10,
                "azimuth": 180,
                "modules_per_string": 20,
                "strings": 5,
                "coords": [[101.69, 3.14], [101.70, 3.14], [101.70, 3.15], [101.69, 3.15], [101.69, 3.14]],
            }
        ],
        "module_specs": {
            "Test Module": {
                "name": "Test Module",
                "p_max": 650,
                "voc": 48.0,
                "isc": 17.0,
                "vmp": 40.0,
                "imp": 16.25,
                "length": 2.2,
                "width": 1.1,
            }
        },
        "inverter_specs": {
            "Test Inverter": {
                "name": "Test Inverter",
                "p_aco": 50000,
                "vdcmax": 1000,
                "vdcmin": 200,
            }
        },
    }


def test_valid_project():
    p = _minimal_project()
    validated = SimulationInput.model_validate(p)
    assert validated.name == "Test"
    assert len(validated.arrays) == 1
    assert validated.arrays[0].module == "Test Module"
    assert validated.module_specs["Test Module"].p_max == 650


def test_missing_module_spec_raises():
    p = _minimal_project()
    p["arrays"][0]["module"] = "Unknown Module"
    with pytest.raises(Exception):
        SimulationInput.model_validate(p)


def test_missing_inverter_spec_raises():
    p = _minimal_project()
    p["arrays"][0]["inverter"] = "Unknown Inverter"
    with pytest.raises(Exception):
        SimulationInput.model_validate(p)


def test_extra_fields_allowed():
    p = _minimal_project()
    p["custom_field"] = "extra"
    validated = SimulationInput.model_validate(p)
    assert validated.model_dump()["custom_field"] == "extra"
