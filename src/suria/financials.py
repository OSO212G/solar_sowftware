"""Solar ATAP simple financial model."""

# TNB tariff blocks (2026 estimate)
TNB_TARIFF = {
    "A": 0.218,   # Domestic ≤ 200 kWh
    "B": 0.334,   # Domestic 201-300 kWh
    "C": 0.516,   # Domestic 301-600 kWh
    "D": 0.546,   # Domestic 601-900 kWh
    "E1": 0.571,  # Commercial low voltage
    "E2": 0.505,  # Commercial medium voltage
}

# Solar ATAP export rate (displaced cost / SMP)
SOLAR_ATAP_EXPORT_RATE = 0.25  # RM/kWh — verify with current TNB rate


def calculate_financials(annual_kwh, system_cost_rm, self_consumption_pct=0.70, tariff_block="E1", export_rate_rm_per_kwh=None, annual_degradation_pct=0.5):
    """Simple Solar ATAP financial estimate."""
    tariff = TNB_TARIFF.get(tariff_block, TNB_TARIFF["E1"])
    export_rate = export_rate_rm_per_kwh if export_rate_rm_per_kwh is not None else SOLAR_ATAP_EXPORT_RATE
    degradation = annual_degradation_pct / 100

    self_consumption_kwh = annual_kwh * self_consumption_pct
    export_kwh = annual_kwh * (1 - self_consumption_pct)

    savings_rm = self_consumption_kwh * tariff
    export_income_rm = export_kwh * export_rate
    total_annual_benefit_rm = savings_rm + export_income_rm

    simple_payback_years = system_cost_rm / total_annual_benefit_rm if total_annual_benefit_rm > 0 else float("inf")

    # Payback with degradation (year-by-year cumulative)
    cumulative = 0.0
    payback_with_degradation = None
    year_benefits = []
    current_annual = total_annual_benefit_rm
    for year in range(1, 26):
        cumulative += current_annual
        year_benefits.append({"year": year, "benefit": round(current_annual, 0), "cumulative": round(cumulative, 0)})
        if payback_with_degradation is None and cumulative >= system_cost_rm:
            payback_with_degradation = year - 1 + (system_cost_rm - (cumulative - current_annual)) / current_annual
        current_annual *= (1 - degradation)

    if payback_with_degradation is None:
        payback_with_degradation = float("inf")

    return {
        "tariff_rm_per_kwh": tariff,
        "export_rate_rm_per_kwh": export_rate,
        "self_consumption_kwh": self_consumption_kwh,
        "export_kwh": export_kwh,
        "savings_rm": savings_rm,
        "export_income_rm": export_income_rm,
        "total_annual_benefit_rm": total_annual_benefit_rm,
        "simple_payback_years": simple_payback_years,
        "payback_with_degradation_years": round(payback_with_degradation, 1),
        "total_25yr_benefit_rm": round(cumulative, 0),
        "yearly_benefits": year_benefits,
        "annual_degradation_pct": annual_degradation_pct,
    }
