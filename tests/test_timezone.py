"""Tests for timezone helper."""
from suria.timezone import get_timezone


def test_explicit_tz():
    assert get_timezone(3.14, 101.69, tz="Asia/Kuala_Lumpur") == "Asia/Kuala_Lumpur"


def test_kuala_lumpur_approx():
    # lon ~101 → round(101/15) = 7 → Etc/GMT-7 (UTC+7)
    assert get_timezone(3.14, 101.69) == "Etc/GMT-7"


def test_manila_approx():
    # lon ~123 → round(123/15) = 8 → Etc/GMT-8 (UTC+8)
    assert get_timezone(8.5, 123.0) == "Etc/GMT-8"


def test_western_longitude():
    # lon ~-74 (New York) → round(-74/15) = -5 → Etc/GMT+5 (UTC-5)
    assert get_timezone(40.7, -74.0) == "Etc/GMT+5"
