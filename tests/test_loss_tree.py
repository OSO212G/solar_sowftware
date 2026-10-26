"""Tests for canonical loss tree."""
from suria.engine.loss_tree import LossEntry, LossTree


def test_lossless_tree():
    """Zero losses → grid = nameplate."""
    tree = LossTree(nameplate_kwh=1000.0)
    result = tree.compute()
    assert result == 1000.0


def test_single_loss():
    """10% soiling alone → 900 kWh."""
    tree = LossTree(nameplate_kwh=1000.0)
    tree.soiling = LossEntry(pct=10.0, energy_lost_kwh=100.0, source="config")
    result = tree.compute()
    assert result == 900.0


def test_cumulative_losses():
    """Two 10% losses compound multiplicatively."""
    tree = LossTree(nameplate_kwh=1000.0)
    tree.soiling = LossEntry(pct=10.0, energy_lost_kwh=100.0, source="config")
    tree.temperature = LossEntry(pct=10.0, energy_lost_kwh=90.0, source="pvlib")
    result = tree.compute()
    assert result == 810.0


def test_bifacial_gain():
    """Negative bifaciality adds energy."""
    tree = LossTree(nameplate_kwh=1000.0)
    tree.bifaciality = LossEntry(pct=-5.0, energy_lost_kwh=-50.0, source="config")
    result = tree.compute()
    assert result == 1050.0


def test_diagnostic_summary_length():
    """Summary has 13 rows (Nameplate + 11 losses + Grid)."""
    tree = LossTree(nameplate_kwh=1000.0)
    tree.soiling = LossEntry(pct=2.0, energy_lost_kwh=20.0, source="config")
    tree.compute()
    summary = tree.diagnostic_summary()
    assert len(summary) == 13
    assert summary[0]["step"] == "Nameplate"
    assert summary[-1]["step"] == "Grid"
