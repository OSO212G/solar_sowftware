"""Tests for shading and layout calculations."""
from suria.simulate import simulate_array
from suria.layout import calculate_row_spacing


def test_calculate_row_spacing_produces_positive_spacing():
    """Row spacing must be positive for typical inputs."""
    spacing = calculate_row_spacing(10, 1.134)
    assert spacing > 0


def test_gcr_is_reasonable():
    """Ground Coverage Ratio should be a sensible fraction between 0 and 1."""
    panel_height = 1.134
    spacing = calculate_row_spacing(10, panel_height)
    gcr = panel_height / spacing
    assert 0 < gcr < 1
