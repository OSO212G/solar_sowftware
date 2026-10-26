"""Solar ATAP sizing validation for Malaysia.

Validates system capacity against SEDA/TNB Solar Self-Consumption
(formerly Net Energy Metering 3.0) rules and guidelines.

References:
- SEDA Malaysia Solar ATAP programme guidelines (2026)
- TNB tariff structure and connection capacity rules
"""
from suria.domain.simulation_input import SimulationInput

# NEM 3.0 hard capacity limits by consumer category (kWp DC)
NEM_CAPACITY_LIMITS_KWP = {
    "domestic": 72,
    "commercial_lv": 1000,
    "commercial_mv": 10000,
}

# Typical TNB fuse / breaker ratings by tariff block (Amps)
# These are conservative defaults; user can override.
DEFAULT_FUSE_RATINGS_A = {
    "A": 60,
    "B": 60,
    "C": 100,
    "D": 150,
    "E1": 400,
    "E2": 800,
}

# Nominal single-phase voltage for fuse-limit calculation
_TNB_SINGLE_PHASE_V = 230.0


def _consumer_type_from_tariff(tariff: str) -> str:
    """Infer consumer category from TNB tariff block."""
    if tariff in ("A", "B", "C", "D"):
        return "domestic"
    if tariff == "E1":
        return "commercial_lv"
    return "commercial_mv"


def validate_nem_sizing(
    project: dict,
    consumer_type: str = "auto",
    fuse_rating_a: float | None = None,
    max_demand_kw: float | None = None,
) -> dict:
    """Validate a project against Solar ATAP sizing rules.

    Returns a dict with:
      - issues: list of dicts (severity, code, message)
      - dc_kw, ac_kw, dc_ac_ratio
      - consumer_type, applicable_limit_kw, nem_eligible
    """
    validated = SimulationInput.model_validate(project)
    project = validated.model_dump()
    issues = []

    dc_kw = sum(
        a["modules_per_string"] * a["strings"] * project["module_specs"][a["module"]]["p_max"] / 1000
        for a in project["arrays"]
    )
    ac_kw = sum(
        project["inverter_specs"][a["inverter"]]["p_aco"] / 1000
        for a in project["arrays"]
    )
    ratio = dc_kw / ac_kw if ac_kw > 0 else float("inf")

    tariff = project.get("tariff_block", "E1")
    if consumer_type == "auto":
        consumer_type = _consumer_type_from_tariff(tariff)

    # --- DC:AC ratio ---
    if ratio > 1.35:
        issues.append({
            "severity": "error",
            "code": "nem_dc_ac_ratio_exceeded",
            "message": f"DC:AC ratio {ratio:.2f} exceeds Solar ATAP maximum of 1.35. "
                       "Reduce DC capacity or increase inverter size.",
        })
    elif ratio > 1.30:
        issues.append({
            "severity": "warning",
            "code": "nem_dc_ac_ratio_near_limit",
            "message": f"DC:AC ratio {ratio:.2f} is close to Solar ATAP limit of 1.35. "
                       "TNB recommends ≤1.30 for best practice.",
        })

    # --- Capacity limits ---
    hard_limit = NEM_CAPACITY_LIMITS_KWP.get(consumer_type, 10000)

    if consumer_type == "domestic":
        fuse = fuse_rating_a if fuse_rating_a is not None else DEFAULT_FUSE_RATINGS_A.get(tariff, 60)
        # Conservative: 100% of fuse rating at single-phase 230 V
        fuse_limit_kw = fuse * _TNB_SINGLE_PHASE_V / 1000
        applicable_limit = min(hard_limit, fuse_limit_kw)

        if dc_kw > applicable_limit:
            issues.append({
                "severity": "error",
                "code": "nem_capacity_exceeded_domestic",
                "message": f"DC capacity {dc_kw:.1f} kWp exceeds domestic Solar ATAP limit of "
                           f"{applicable_limit:.1f} kWp (lower of {hard_limit} kWp or "
                           f"{fuse_limit_kw:.1f} kWp from {fuse:.0f} A fuse rating).",
            })
        else:
            issues.append({
                "severity": "info",
                "code": "nem_capacity_ok",
                "message": f"DC capacity {dc_kw:.1f} kWp is within domestic Solar ATAP limit of "
                           f"{applicable_limit:.1f} kWp.",
            })

    else:
        # Commercial LV / MV
        if max_demand_kw is not None and max_demand_kw > 0:
            md_limit = max_demand_kw * 0.75
            applicable_limit = min(hard_limit, md_limit)
        else:
            md_limit = None
            applicable_limit = hard_limit

        if dc_kw > applicable_limit:
            msg = (
                f"DC capacity {dc_kw:.1f} kWp exceeds commercial Solar ATAP limit of "
                f"{applicable_limit:.1f} kWp."
            )
            if md_limit is not None:
                msg += f" (75% of {max_demand_kw:.1f} kW max demand = {md_limit:.1f} kWp)."
            issues.append({
                "severity": "error",
                "code": "nem_capacity_exceeded_commercial",
                "message": msg,
            })
        else:
            msg = f"DC capacity {dc_kw:.1f} kWp is within commercial Solar ATAP limit of {applicable_limit:.1f} kWp."
            issues.append({
                "severity": "info",
                "code": "nem_capacity_ok",
                "message": msg,
            })

    # --- Eligibility summary ---
    nem_eligible = dc_kw <= applicable_limit and ratio <= 1.35
    if nem_eligible:
        issues.append({
            "severity": "info",
            "code": "nem_eligible",
            "message": "System is eligible for Solar ATAP self-consumption.",
        })
    else:
        issues.append({
            "severity": "warning",
            "code": "nem_not_eligible",
            "message": "System does not meet Solar ATAP sizing rules. "
                       "Consider splitting into multiple accounts or reducing DC capacity.",
        })

    return {
        "issues": issues,
        "dc_kw": round(dc_kw, 2),
        "ac_kw": round(ac_kw, 2),
        "dc_ac_ratio": round(ratio, 2),
        "consumer_type": consumer_type,
        "applicable_limit_kw": round(applicable_limit, 2),
        "nem_eligible": nem_eligible,
    }
