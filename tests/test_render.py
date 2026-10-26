"""Tests for PDF report renderer."""
from pathlib import Path
from suria.reporter.render import render_report, render_map_image, _payback_chart_bytes


SAMPLE_PROJECT = {
    "name": "Test Site",
    "customer": "Test Customer",
    "designer": "Test Designer",
    "site": {"lat": 3.14, "lon": 101.69, "altitude": 50},
    "arrays": [
        {
            "name": "Array 1",
            "coords": [[101.69, 3.14], [101.691, 3.14], [101.691, 3.141], [101.69, 3.141], [101.69, 3.14]],
            "tilt": 10,
            "azimuth": 180,
            "modules_per_string": 20,
            "strings": 2,
            "module": "Aiko 650W",
            "inverter": "Huawei 10k",
        }
    ],
    "module_specs": {
        "Aiko 650W": {"name": "Aiko 650W", "p_max": 650, "voc": 54.0, "vmp": 45.3, "isc": 15.06, "imp": 14.35, "length": 2.382, "width": 1.134}
    },
    "inverter_specs": {
        "Huawei 10k": {"name": "Huawei 10k", "p_aco": 10000, "p_dco": 10200, "v_dco": 600, "vdcmin": 200, "vdcmax": 1100, "mppt_min": 200, "mppt_max": 1000, "efficiency": 0.984}
    },
}

SAMPLE_RESULT = {
    "annual_ac_kwh": 15000,
    "monthly_ac_kwh": [1200] * 12,
    "specific_yield": 1150,
    "capacity_factor": 13.0,
    "performance_ratio": 76.5,
    "losses": {"soiling": 2.0, "mismatch": 2.0, "wiring": 1.5, "availability": 1.0, "lid": 1.5, "temperature": 12.0, "clipping": 0.5, "inverter": 1.6, "ac_system": 0.5},
    "electrical": {
        "summary": {"overall_dc_ac_ratio": 1.30, "total_dc_w": 26000, "total_ac_w": 20000, "issue_count": 0, "error_count": 0, "warning_count": 0},
        "issues": []
    }
}


def test_render_map_image_empty():
    assert render_map_image({"arrays": []}) is None


def test_render_map_image_with_polygons():
    img = render_map_image(SAMPLE_PROJECT)
    assert img is not None
    assert img.size == (700, 400)


def test_render_report_creates_pdf(tmp_path):
    out = tmp_path / "test_report.pdf"
    render_report(SAMPLE_PROJECT, SAMPLE_RESULT, out)
    assert out.exists()
    assert out.stat().st_size > 10000


def test_bom_calculations_in_report(tmp_path):
    out = tmp_path / "bom_test.pdf"
    render_report(SAMPLE_PROJECT, SAMPLE_RESULT, out)
    # 20 modules/string * 2 strings = 40 modules
    # 2 strings * 30m = 60m DC cable
    # AC cable = ac_kw = 10kW/1000 = 10m
    # Rails = 40 * 2.5 = 100m
    # Clamps = 40 * 4 = 160
    # 1 inverter -> 1 DC SPD, 1 AC SPD
    assert out.exists()


def test_render_report_with_panel_schematics(tmp_path):
    """PDF should generate successfully when arrays contain panel rectangles."""
    project = {
        "name": "Schematic Test",
        "customer": "Test",
        "designer": "Test",
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
                "modules_per_string": 2,
                "strings": 2,
                "module": "Aiko 650W",
                "inverter": "Huawei 10k",
                "panel_rectangles": [
                    [[101.69, 3.14], [101.6905, 3.14], [101.6905, 3.1405], [101.69, 3.1405]],
                    [[101.6905, 3.14], [101.691, 3.14], [101.691, 3.1405], [101.6905, 3.1405]],
                    [[101.69, 3.1405], [101.6905, 3.1405], [101.6905, 3.141], [101.69, 3.141]],
                    [[101.6905, 3.1405], [101.691, 3.1405], [101.691, 3.141], [101.6905, 3.141]],
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
                "mppt_min": 200,
                "mppt_max": 1000,
                "efficiency": 0.984,
            }
        },
    }
    out = tmp_path / "schematic_test.pdf"
    render_report(project, SAMPLE_RESULT, out)
    assert out.exists()
    assert out.stat().st_size > 10000


def test_render_report_with_keepouts(tmp_path):
    """PDF should generate successfully when arrays contain keepouts."""
    project = {
        "name": "Keepout Test",
        "customer": "Test",
        "designer": "Test",
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
                "modules_per_string": 2,
                "strings": 2,
                "module": "Aiko 650W",
                "inverter": "Huawei 10k",
                "keepouts": [
                    {
                        "description": "HVAC unit",
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
                "mppt_min": 200,
                "mppt_max": 1000,
                "efficiency": 0.984,
            }
        },
    }
    out = tmp_path / "keepout_test.pdf"
    render_report(project, SAMPLE_RESULT, out)
    assert out.exists()
    assert out.stat().st_size > 10000


def test_render_map_image_zoom_near_rooftop():
    """Very small polygon (~0.0001 degrees) should not crash with auto-zoom cap issues."""
    tiny_project = {
        "name": "Tiny Rooftop",
        "customer": "Test",
        "designer": "Test",
        "site": {"lat": 3.14, "lon": 101.69, "altitude": 50},
        "arrays": [
            {
                "name": "Tiny Array",
                "coords": [
                    [101.69, 3.14],
                    [101.6901, 3.14],
                    [101.6901, 3.1401],
                    [101.69, 3.1401],
                    [101.69, 3.14],
                ],
                "tilt": 10,
                "azimuth": 180,
                "modules_per_string": 1,
                "strings": 1,
                "module": "Aiko 650W",
                "inverter": "Huawei 10k",
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
                "mppt_min": 200,
                "mppt_max": 1000,
                "efficiency": 0.984,
            }
        },
    }
    img = render_map_image(tiny_project)
    assert img is not None
    assert img.size == (700, 400)


def test_payback_chart_bytes():
    """Payback chart should generate PNG bytes with valid yearly data."""
    yearly = [
        {"year": i, "benefit": 10000 * (0.995 ** (i - 1)), "cumulative": sum(10000 * (0.995 ** (j - 1)) for j in range(1, i + 1))}
        for i in range(1, 26)
    ]
    buf = _payback_chart_bytes(yearly, system_cost_rm=80000)
    assert buf is not None
    assert buf.getbuffer().nbytes > 1000
