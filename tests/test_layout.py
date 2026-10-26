"""Tests for panel layout engine."""
import pytest
from suria.layout import estimate_panels_from_polygon, calculate_row_spacing
from suria.domain.frame import make_frame, to_xy, to_latlon


class TestCalculateRowSpacing:
    def test_basic_spacing(self):
        spacing = calculate_row_spacing(tilt_deg=10, panel_height_m=1.134)
        assert spacing > 1.134 * 0.5
        assert spacing > 0

    def test_zero_tilt(self):
        spacing = calculate_row_spacing(tilt_deg=0, panel_height_m=1.0)
        # At 0 tilt, spacing should be minimal (just panel height * 0.5 floor)
        assert spacing >= 0.5


class TestFrameRoundTrip:
    def test_round_trip(self):
        lat, lon = 3.14, 101.69
        frame = make_frame(lat, lon)
        x, y = to_xy(frame, lon, lat)
        lon_back, lat_back = to_latlon(frame, x, y)
        assert abs(lat_back - lat) < 1e-6
        assert abs(lon_back - lon) < 1e-6


class TestEstimatePanelsFromPolygon:
    def test_empty_coords(self):
        count, centers, rectangles = estimate_panels_from_polygon([], 2.0, 1.0, 2.0, 0.5)
        assert count == 0
        assert centers == []
        assert rectangles == []

    def test_simple_rectangle(self):
        # Approx 10m x 10m square near Kuala Lumpur
        # Using rough conversion: 0.0001 deg ≈ 11m
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        count, centers, rectangles = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0)
        # Should fit some panels in a ~10x10m area
        assert count > 0
        assert len(centers) == count
        assert len(rectangles) == count
        assert all(len(rect) == 4 for rect in rectangles)

    def test_setback_reduces_count(self):
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        count_no_setback, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0)
        count_with_setback, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 1.0)
        assert count_with_setback <= count_no_setback

    def test_portrait_fits_different_count(self):
        """Portrait vs landscape should produce different counts on a narrow roof."""
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        count_landscape, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0, portrait=False)
        count_portrait, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0, portrait=True)
        # Portrait should fit more panels in a ~10x10m area because the x-step is narrower
        assert count_portrait > count_landscape

    def test_azimuth_rotation_same_count_for_square(self):
        """A square roof rotated 90° should fit the same number of panels."""
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        count_180, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0, azimuth=180)
        count_90, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0, azimuth=90)
        # Square looks identical under 90° rotation, so counts should match
        assert count_90 == count_180

    def test_keepout_excludes_panels(self):
        """A keepout polygon inside the array should exclude panels."""
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        # Small keepout in the center (~5m x 5m)
        ko_delta = delta * 0.5
        keepout_coords = [
            [lon, lat]
            for lon, lat in [
                (101.69 + delta * 0.25, 3.14 + delta * 0.25),
                (101.69 + delta * 0.75, 3.14 + delta * 0.25),
                (101.69 + delta * 0.75, 3.14 + delta * 0.75),
                (101.69 + delta * 0.25, 3.14 + delta * 0.75),
                (101.69 + delta * 0.25, 3.14 + delta * 0.25),
            ]
        ]
        count_no_ko, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0)
        count_with_ko, _, _ = estimate_panels_from_polygon(
            coords, 2.0, 1.0, 2.0, 0.0, keepouts=[{"coords": keepout_coords, "active": True}]
        )
        assert count_with_ko < count_no_ko

    def test_inactive_keepout_does_not_exclude(self):
        """An inactive keepout should not affect panel count."""
        delta = 0.0001
        coords = [
            [lon, lat]
            for lon, lat in [
                (101.69, 3.14),
                (101.69 + delta, 3.14),
                (101.69 + delta, 3.14 + delta),
                (101.69, 3.14 + delta),
                (101.69, 3.14),
            ]
        ]
        ko_delta = delta * 0.5
        keepout_coords = [
            [lon, lat]
            for lon, lat in [
                (101.69 + delta * 0.25, 3.14 + delta * 0.25),
                (101.69 + delta * 0.75, 3.14 + delta * 0.25),
                (101.69 + delta * 0.75, 3.14 + delta * 0.75),
                (101.69 + delta * 0.25, 3.14 + delta * 0.75),
                (101.69 + delta * 0.25, 3.14 + delta * 0.25),
            ]
        ]
        count_no_ko, _, _ = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.0)
        count_inactive_ko, _, _ = estimate_panels_from_polygon(
            coords, 2.0, 1.0, 2.0, 0.0, keepouts=[{"coords": keepout_coords, "active": False}]
        )
        assert count_inactive_ko == count_no_ko
