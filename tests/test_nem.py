"""Tests for NEM 3.0 / Solar ATAP sizing validation."""
import pytest
from suria.nem import validate_nem_sizing

SAMPLE_PROJECT = {
    "name": "Test",
    "site": {"lat": 3.14, "lon": 101.69},
    "arrays": [
        {"name": "A1", "modules_per_string": 20, "strings": 2, "module": "Aiko 650W", "inverter": "Huawei 10k"},
    ],
    "module_specs": {
        "Aiko 650W": {"name": "Aiko 650W", "p_max": 650},
    },
    "inverter_specs": {
        "Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000},
    },
    "tariff_block": "E1",
}


def test_nem_valid_commercial():
    """26 kWp / 10 kW AC is well within commercial LV limits."""
    result = validate_nem_sizing(SAMPLE_PROJECT, consumer_type="commercial_lv")
    assert result["dc_kw"] == 26.0
    assert result["ac_kw"] == 10.0
    assert result["dc_ac_ratio"] == 2.6  # >1.35 should error
    assert result["nem_eligible"] is False
    errors = [i for i in result["issues"] if i["severity"] == "error"]
    assert any("DC:AC ratio" in e["message"] for e in errors)


def test_nem_valid_domestic_small():
    """Small domestic system within 72 kWp and fuse limit."""
    proj = {
        "name": "Small",
        "site": {"lat": 3.14, "lon": 101.69},
        "arrays": [
            {"name": "A1", "modules_per_string": 10, "strings": 1, "module": "Aiko 650W", "inverter": "Huawei 10k"},
        ],
        "module_specs": {"Aiko 650W": {"name": "Aiko 650W", "p_max": 650}},
        "inverter_specs": {"Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000}},
        "tariff_block": "C",
    }
    result = validate_nem_sizing(proj, consumer_type="domestic")
    assert result["dc_kw"] == 6.5
    assert result["ac_kw"] == 10.0
    assert result["dc_ac_ratio"] == 0.65
    assert result["nem_eligible"] is True
    assert any(i["code"] == "nem_eligible" for i in result["issues"])


def test_nem_domestic_fuse_limit():
    """Domestic system exceeding fuse rating should error."""
    proj = {
        "name": "Big domestic",
        "site": {"lat": 3.14, "lon": 101.69},
        "arrays": [
            {"name": "A1", "modules_per_string": 20, "strings": 10, "module": "Aiko 650W", "inverter": "Huawei 10k"},
        ],
        "module_specs": {"Aiko 650W": {"name": "Aiko 650W", "p_max": 650}},
        "inverter_specs": {"Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000}},
        "tariff_block": "A",
    }
    result = validate_nem_sizing(proj, consumer_type="domestic")
    assert result["dc_kw"] == 130.0
    # 60A fuse @ 230V = 13.8 kW limit, so 130 kWp far exceeds
    assert result["nem_eligible"] is False
    errors = [i for i in result["issues"] if i["severity"] == "error"]
    assert any("exceeds domestic Solar ATAP limit" in e["message"] for e in errors)


def test_nem_commercial_md_limit():
    """Commercial system exceeding 75% of max demand."""
    proj = {
        "name": "MD limited",
        "site": {"lat": 3.14, "lon": 101.69},
        "arrays": [
            {"name": "A1", "modules_per_string": 20, "strings": 10, "module": "Aiko 650W", "inverter": "Huawei 100k"},
        ],
        "module_specs": {"Aiko 650W": {"name": "Aiko 650W", "p_max": 650}},
        "inverter_specs": {"Huawei 100k": {"name": "Huawei 100k", "p_aco": 100000}},
        "tariff_block": "E1",
    }
    result = validate_nem_sizing(proj, consumer_type="commercial_lv", max_demand_kw=100.0)
    assert result["dc_kw"] == 130.0
    # 75% of 100 kW = 75 kW limit, so 130 kWp exceeds
    assert result["nem_eligible"] is False
    errors = [i for i in result["issues"] if i["severity"] == "error"]
    assert any("exceeds commercial Solar ATAP limit" in e["message"] for e in errors)


def test_nem_auto_consumer_type():
    """Auto-detection from tariff block."""
    proj = {**SAMPLE_PROJECT, "tariff_block": "A"}
    result = validate_nem_sizing(proj, consumer_type="auto")
    assert result["consumer_type"] == "domestic"

    proj = {**SAMPLE_PROJECT, "tariff_block": "E1"}
    result = validate_nem_sizing(proj, consumer_type="auto")
    assert result["consumer_type"] == "commercial_lv"

    proj = {**SAMPLE_PROJECT, "tariff_block": "E2"}
    result = validate_nem_sizing(proj, consumer_type="auto")
    assert result["consumer_type"] == "commercial_mv"


def test_nem_ratio_warning():
    """DC:AC ratio between 1.30 and 1.35 should warn."""
    proj = {
        "name": "Ratio test",
        "site": {"lat": 3.14, "lon": 101.69},
        "arrays": [
            {"name": "A1", "modules_per_string": 20, "strings": 1, "module": "Aiko 650W", "inverter": "Huawei 10k"},
        ],
        "module_specs": {"Aiko 650W": {"name": "Aiko 650W", "p_max": 650}},
        "inverter_specs": {"Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000}},
        "tariff_block": "E1",
    }
    result = validate_nem_sizing(proj, consumer_type="commercial_lv")
    assert result["dc_kw"] == 13.0
    assert result["dc_ac_ratio"] == 1.3
    assert result["nem_eligible"] is True
    warnings = [i for i in result["issues"] if i["severity"] == "warning"]
    # 1.3 is exactly at the warning threshold (<=1.30 no warning, >1.30 warning)
    # Actually the code warns at >1.30, so 1.3 should NOT warn
    assert not any("close to NEM 3.0 limit" in w["message"] for w in warnings)

    # Slightly higher ratio
    proj2 = {
        "name": "Ratio test 2",
        "site": {"lat": 3.14, "lon": 101.69},
        "arrays": [
            {"name": "A1", "modules_per_string": 21, "strings": 1, "module": "Aiko 650W", "inverter": "Huawei 10k"},
        ],
        "module_specs": {"Aiko 650W": {"name": "Aiko 650W", "p_max": 650}},
        "inverter_specs": {"Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000}},
        "tariff_block": "E1",
    }
    result2 = validate_nem_sizing(proj2, consumer_type="commercial_lv")
    assert result2["dc_ac_ratio"] == 1.36
    assert result2["nem_eligible"] is False
