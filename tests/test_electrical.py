"""Tests for electrical validation."""
import pytest
from suria.electrical import validate_array_electrical, validate_project_electrical, validate_string_config


SAMPLE_MODULE = {
    "name": "Test 550W",
    "p_max": 550,
    "voc": 49.8,
    "vmp": 41.8,
    "isc": 14.12,
    "imp": 13.17,
    "temp_coeff_voc": -0.28,
    "temp_coeff_pmax": -0.35,
    "length": 2.278,
    "width": 1.134,
}

SAMPLE_INVERTER = {
    "name": "Test 40k",
    "p_aco": 40000,
    "p_dco": 44000,
    "v_dco": 720,
    "vdcmin": 200,
    "vdcmax": 1100,
    "mppt_min": 250,
    "mppt_max": 1000,
    "efficiency": 0.985,
}


class TestValidateArrayElectrical:
    def test_valid_design_no_issues(self):
        array = {
            "modules_per_string": 14,
            "strings": 2,
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, SAMPLE_INVERTER)
        errors = sum(1 for i in res["issues"] if i["severity"] == "error")
        assert errors == 0
        warnings = sum(1 for i in res["issues"] if i["severity"] == "warning")
        assert warnings == 0
        assert res["dc_ac_ratio"] < 1.35

    def test_voc_exceeds_vdcmax(self):
        array = {
            "modules_per_string": 25,  # 25 * 49.8V = 1245V > 1100V
            "strings": 1,
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, SAMPLE_INVERTER)
        assert any(i["code"] == "voc_exceeds_vdcmax" for i in res["issues"])
        errors = sum(1 for i in res["issues"] if i["severity"] == "error")
        assert errors >= 1

    def test_high_dc_ac_ratio(self):
        array = {
            "modules_per_string": 20,
            "strings": 10,  # 200 modules * 550W = 110kW DC into 40kW AC
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, SAMPLE_INVERTER)
        assert any(i["code"] == "dc_ac_ratio_high" for i in res["issues"])

    def test_low_dc_ac_ratio(self):
        array = {
            "modules_per_string": 5,
            "strings": 1,  # 2750W DC into 40000W AC
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, SAMPLE_INVERTER)
        assert any(i["code"] == "dc_ac_ratio_low" for i in res["issues"])

    def test_imp_exceeds_mppt_max_a(self):
        inv = {**SAMPLE_INVERTER, "idcmax": 20.0, "mppt_max_a": 13.0}
        array = {
            "modules_per_string": 14,
            "strings": 1,
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        assert any(i["code"] == "imp_exceeds_mppt_max_a" for i in res["issues"])
        # Existing isc vs idcmax check should NOT fire because idcmax is 20 A
        assert not any(i["code"] == "isc_exceeds_idcmax" for i in res["issues"])

    def test_dc_power_exceeds_p_dco(self):
        array = {
            "modules_per_string": 20,
            "strings": 10,  # 200 modules * 550W = 110 kW DC into 44 kW DC max
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, SAMPLE_INVERTER)
        assert any(i["code"] == "dc_power_exceeds_p_dco" for i in res["issues"])

    def test_per_string_power_high(self):
        inv = {**SAMPLE_INVERTER, "p_dco": 10000}
        array = {
            "modules_per_string": 14,
            "strings": 1,
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        assert any(i["code"] == "per_string_power_high" for i in res["issues"])

    def test_isc_temp_derated_exceeds_idcmax(self):
        inv = {**SAMPLE_INVERTER, "idcmax": 14.5}
        array = {
            "modules_per_string": 14,
            "strings": 1,
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        # Original I_sc at STC (14.12 A) is below 14.5 A, so that check passes
        assert not any(i["code"] == "isc_exceeds_idcmax" for i in res["issues"])
        # But derated I_sc at high temp should exceed 14.5 A
        assert any(i["code"] == "isc_temp_derated_exceeds_idcmax" for i in res["issues"])

    def test_mppt_string_count_exceeded(self):
        inv = {**SAMPLE_INVERTER, "mppt_count": 2, "parallel_strings_max": 2}
        array = {
            "modules_per_string": 14,
            "strings": 5,  # 5 > 2*2 = 4
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        assert any(i["code"] == "mppt_string_count_exceeded" for i in res["issues"])
        errors = sum(1 for i in res["issues"] if i["severity"] == "error")
        assert errors >= 1

    def test_mppt_current_exceeded(self):
        inv = {
            **SAMPLE_INVERTER,
            "mppt_count": 2,
            "parallel_strings_max": 4,
            "mppt_i_max": 20.0,
        }
        array = {
            "modules_per_string": 14,
            "strings": 4,  # 4 strings / 2 MPPTs = 2 per MPPT → 2*13.17=26.34 A > 20 A
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        assert any(i["code"] == "mppt_current_exceeded" for i in res["issues"])
        errors = sum(1 for i in res["issues"] if i["severity"] == "error")
        assert errors >= 1

    def test_mppt_limits_pass(self):
        inv = {
            **SAMPLE_INVERTER,
            "mppt_count": 2,
            "parallel_strings_max": 2,
            "mppt_i_max": 30.0,
        }
        array = {
            "modules_per_string": 14,
            "strings": 2,  # 2 strings / 2 MPPTs = 1 per MPPT → 1*13.17=13.17 A < 30 A
            "module": "Test 550W",
            "inverter": "Test 40k",
        }
        res = validate_array_electrical(array, SAMPLE_MODULE, inv)
        assert not any(i["code"] == "mppt_string_count_exceeded" for i in res["issues"])
        assert not any(i["code"] == "mppt_current_exceeded" for i in res["issues"])


class TestValidateStringConfig:
    def test_valid_string_config(self):
        assert validate_string_config(14, SAMPLE_MODULE, SAMPLE_INVERTER) is True

    def test_invalid_string_config(self):
        # 25 modules * 49.8 V = 1245 V > 1100 Vdcmax
        assert validate_string_config(25, SAMPLE_MODULE, SAMPLE_INVERTER) is False


class TestValidateProjectElectrical:
    def test_multi_array_aggregation(self):
        project = {
            "site": {"lat": 3.14, "lon": 101.69},
            "arrays": [
                {"modules_per_string": 14, "strings": 2, "module": "M1", "inverter": "I1"},
                {"modules_per_string": 14, "strings": 2, "module": "M1", "inverter": "I1"},
            ],
            "module_specs": {"M1": SAMPLE_MODULE},
            "inverter_specs": {"I1": SAMPLE_INVERTER},
        }
        res = validate_project_electrical(project)
        assert res["summary"]["overall_dc_ac_ratio"] > 0
        assert res["summary"]["total_dc_w"] == 2 * (14 * 2 * 550)
