"""Tests for Solar ATAP financials."""
import pytest
from suria.financials import calculate_financials, TNB_TARIFF


class TestCalculateFinancials:
    def test_basic_commercial(self):
        fin = calculate_financials(annual_kwh=10000, system_cost_rm=350000, self_consumption_pct=0.70, tariff_block="E1")
        assert fin["tariff_rm_per_kwh"] == TNB_TARIFF["E1"]
        assert fin["self_consumption_kwh"] == pytest.approx(7000)
        assert fin["export_kwh"] == pytest.approx(3000)
        assert fin["total_annual_benefit_rm"] == pytest.approx(7000 * TNB_TARIFF["E1"] + 3000 * 0.25)
        assert fin["simple_payback_years"] > 0

    def test_domestic_block_a(self):
        fin = calculate_financials(annual_kwh=5000, system_cost_rm=50000, self_consumption_pct=0.80, tariff_block="A")
        assert fin["tariff_rm_per_kwh"] == TNB_TARIFF["A"]

    def test_zero_annual_benefit(self):
        fin = calculate_financials(annual_kwh=0, system_cost_rm=10000, self_consumption_pct=1.0, tariff_block="E1")
        assert fin["simple_payback_years"] == float("inf")

    def test_all_export(self):
        fin = calculate_financials(annual_kwh=10000, system_cost_rm=50000, self_consumption_pct=0.0, tariff_block="E1")
        assert fin["savings_rm"] == 0
        assert fin["export_income_rm"] == 10000 * 0.25

    def test_custom_export_rate(self):
        fin = calculate_financials(annual_kwh=10000, system_cost_rm=50000, self_consumption_pct=0.0, tariff_block="E1", export_rate_rm_per_kwh=0.30)
        assert fin["export_rate_rm_per_kwh"] == 0.30
        assert fin["export_income_rm"] == 10000 * 0.30

    def test_custom_self_consumption(self):
        fin = calculate_financials(annual_kwh=10000, system_cost_rm=50000, self_consumption_pct=0.80, tariff_block="E1")
        assert fin["self_consumption_kwh"] == pytest.approx(8000)
        assert fin["export_kwh"] == pytest.approx(2000)
        assert fin["savings_rm"] == pytest.approx(8000 * TNB_TARIFF["E1"])
        assert fin["export_income_rm"] == pytest.approx(2000 * 0.25)

    def test_degradation_payback(self):
        fin = calculate_financials(annual_kwh=10000, system_cost_rm=50000, self_consumption_pct=1.0, tariff_block="E1", annual_degradation_pct=0.5)
        assert fin["simple_payback_years"] < fin["payback_with_degradation_years"]
        assert fin["total_25yr_benefit_rm"] > 0
        assert len(fin["yearly_benefits"]) == 25
