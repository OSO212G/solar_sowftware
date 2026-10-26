"""Electrical validation — string sizing, voltage limits, DC:AC ratio."""
import math

from suria.domain.simulation_input import SimulationInput

# Malaysian design margin: lowest expected ambient for V_oc derating
MIN_DESIGN_TEMP_C = 15.0  # conservative for Malaysia (high temps dominate)

# Module temperature at STC
T_STC = 25.0

# Default temperature coefficient for Isc (%/°C) when not provided.
# Solar cell short-circuit current rises slightly with temperature.
DEFAULT_TEMP_COEFF_ISC = 0.05

# Sanity-check limit for per-string DC power (W).
PER_STRING_POWER_SANITY_LIMIT_W = 20000


def max_string_voltage(voc_stc, temp_coeff_voc_pct_per_c, min_temp_c, module_count):
    """Max string V_oc at lowest expected ambient temperature."""
    delta_t = min_temp_c - T_STC
    voc_at_min = voc_stc * (1 + (temp_coeff_voc_pct_per_c / 100) * delta_t)
    return voc_at_min * module_count


def min_string_voltage(vmp_stc, temp_coeff_pmax_pct_per_c, max_temp_c, module_count):
    """Min string V_mp at highest cell temperature (approx)."""
    # Rough approximation: V_mp drops similarly to V_oc
    # Use Pmax temp coeff as proxy for V_mp temp coeff if not given
    delta_t = max_temp_c - T_STC
    vmp_at_max = vmp_stc * (1 + (temp_coeff_pmax_pct_per_c / 100) * delta_t)
    return vmp_at_max * module_count


def isc_at_temperature(isc_stc, temp_coeff_isc_pct_per_c, cell_temp_c):
    """I_sc at a given cell temperature."""
    delta_t = cell_temp_c - T_STC
    return isc_stc * (1 + (temp_coeff_isc_pct_per_c / 100) * delta_t)


def _resolve_idcmax(inverter_spec):
    """Return the best available inverter DC current limit (A)."""
    explicit_idcmax = inverter_spec.get("idcmax")
    mppt_max_a = inverter_spec.get("mppt_max_a")
    p_dco = inverter_spec.get("p_dco")
    v_dco = inverter_spec.get("v_dco", 0)

    if explicit_idcmax is not None:
        return explicit_idcmax
    if mppt_max_a is not None:
        return mppt_max_a
    if p_dco and v_dco > 0:
        return p_dco / v_dco
    return float("inf")


def validate_array_electrical(array, module_spec, inverter_spec, max_ambient_c=45.0):
    """Return list of warnings/errors for an array's electrical design."""
    issues = []
    n = array["modules_per_string"]
    voc = module_spec["voc"]
    vmp = module_spec["vmp"]
    isc = module_spec["isc"]
    imp = module_spec["imp"]
    temp_coeff_voc = module_spec["temp_coeff_voc"]
    temp_coeff_pmax = module_spec["temp_coeff_pmax"]
    temp_coeff_isc = module_spec.get("temp_coeff_isc", DEFAULT_TEMP_COEFF_ISC)

    vdcmax = inverter_spec["vdcmax"]
    vdcmin = inverter_spec["vdcmin"]
    mppt_min = inverter_spec["mppt_min"]
    mppt_max = inverter_spec["mppt_max"]
    p_aco = inverter_spec["p_aco"]
    p_dco = inverter_spec.get("p_dco")
    mppt_max_a = inverter_spec.get("mppt_max_a")

    idcmax = _resolve_idcmax(inverter_spec)
    max_cell_temp = max_ambient_c + 35.0

    # 1. Max string voltage vs inverter absolute maximum
    v_max = max_string_voltage(voc, temp_coeff_voc, MIN_DESIGN_TEMP_C, n)
    if v_max > vdcmax:
        issues.append({
            "severity": "error",
            "code": "voc_exceeds_vdcmax",
            "message": f"String V_oc max ({v_max:.1f} V) exceeds inverter Vdcmax ({vdcmax:.1f} V). Reduce modules per string or choose higher-voltage inverter.",
        })
    elif v_max > 0.95 * vdcmax:
        issues.append({
            "severity": "warning",
            "code": "voc_near_limit",
            "message": f"String V_oc max ({v_max:.1f} V) is within 5% of inverter Vdcmax ({vdcmax:.1f} V).",
        })

    # 2. Min string voltage vs MPPT minimum
    v_min = min_string_voltage(vmp, temp_coeff_pmax, max_cell_temp, n)
    if v_min < mppt_min:
        issues.append({
            "severity": "error",
            "code": "vmp_below_mppt_min",
            "message": f"String V_mp min ({v_min:.1f} V) below inverter MPPT min ({mppt_min:.1f} V). Increase modules per string.",
        })
    elif v_min < 1.05 * mppt_min:
        issues.append({
            "severity": "warning",
            "code": "vmp_near_mppt_min",
            "message": f"String V_mp min ({v_min:.1f} V) is within 5% of MPPT min ({mppt_min:.1f} V).",
        })

    # 3. Max string voltage vs MPPT maximum
    if v_max > mppt_max:
        issues.append({
            "severity": "warning",
            "code": "voc_above_mppt_max",
            "message": f"String V_oc max ({v_max:.1f} V) exceeds MPPT max ({mppt_max:.1f} V). Inverter may clip at cold start.",
        })

    # 4. String short-circuit current vs inverter absolute DC current limit
    if isc > idcmax:
        issues.append({
            "severity": "error",
            "code": "isc_exceeds_idcmax",
            "message": f"String I_sc ({isc:.2f} A) exceeds inverter Idcmax ({idcmax:.2f} A).",
        })

    # 5. String operating current vs inverter MPPT current limit
    if mppt_max_a is not None and imp > mppt_max_a:
        issues.append({
            "severity": "error",
            "code": "imp_exceeds_mppt_max_a",
            "message": f"String I_mp ({imp:.2f} A) exceeds inverter MPPT max current ({mppt_max_a:.2f} A).",
        })

    # 6. Total DC power vs inverter max DC input
    total_dc_w = n * array["strings"] * module_spec["p_max"]
    if p_dco is not None and total_dc_w > p_dco:
        issues.append({
            "severity": "warning",
            "code": "dc_power_exceeds_p_dco",
            "message": f"Total DC power ({total_dc_w:.0f} W) exceeds inverter max DC input ({p_dco:.0f} W).",
        })

    # 7. Per-string power sanity check
    string_power = n * vmp * imp
    per_string_limit = p_dco / 2 if p_dco else PER_STRING_POWER_SANITY_LIMIT_W
    if string_power > per_string_limit:
        issues.append({
            "severity": "warning",
            "code": "per_string_power_high",
            "message": f"Per-string power ({string_power:.0f} W) is high. Typical per-MPPT limit is around {per_string_limit:.0f} W.",
        })

    # 8. Temperature derating for current — I_sc at high temp vs inverter limits
    isc_high_temp = isc_at_temperature(isc, temp_coeff_isc, max_cell_temp)
    if isc_high_temp > idcmax:
        issues.append({
            "severity": "error",
            "code": "isc_temp_derated_exceeds_idcmax",
            "message": f"I_sc at {max_cell_temp:.0f}°C ({isc_high_temp:.2f} A) exceeds inverter current limit ({idcmax:.2f} A).",
        })

    # 9. MPPT string count limit
    mppt_count = inverter_spec.get("mppt_count", 1)
    parallel_strings_max = inverter_spec.get("parallel_strings_max", 10)
    max_strings_allowed = mppt_count * parallel_strings_max
    if array["strings"] > max_strings_allowed:
        issues.append({
            "severity": "error",
            "code": "mppt_string_count_exceeded",
            "message": f"Strings ({array['strings']}) exceed inverter capacity ({mppt_count} MPPTs × {parallel_strings_max} strings = {max_strings_allowed}).",
        })

    # 10. Per-MPPT current limit (worst-case distribution)
    mppt_i_max = inverter_spec.get("mppt_i_max", 0.0)
    if mppt_i_max > 0 and mppt_count > 0:
        strings_per_mppt = math.ceil(array["strings"] / mppt_count)
        parallel_current = imp * strings_per_mppt
        if parallel_current > mppt_i_max:
            issues.append({
                "severity": "error",
                "code": "mppt_current_exceeded",
                "message": f"Per-MPPT current ({parallel_current:.1f} A = {strings_per_mppt} strings × {imp:.2f} A) exceeds limit ({mppt_i_max:.1f} A).",
            })

    # 11. DC:AC ratio per array
    ratio = total_dc_w / p_aco if p_aco > 0 else float("inf")
    if ratio > 1.35:
        issues.append({
            "severity": "warning",
            "code": "dc_ac_ratio_high",
            "message": f"DC:AC ratio {ratio:.2f} is high (>1.35). Expect clipping losses. TNB recommends ≤1.30 for NEMAS.",
        })
    elif ratio < 1.0:
        issues.append({
            "severity": "info",
            "code": "dc_ac_ratio_low",
            "message": f"DC:AC ratio {ratio:.2f} is conservative (<1.0). Higher DC loading often improves economics under Solar ATAP.",
        })

    return {
        "issues": issues,
        "string_v_max": round(v_max, 1),
        "string_v_min": round(v_min, 1),
        "dc_ac_ratio": round(ratio, 2),
        "strings": array["strings"],
        "modules_per_string": n,
        "total_modules": n * array["strings"],
        "total_dc_w": total_dc_w,
        "inverter_ac_w": p_aco,
        "string_power": round(string_power, 1),
        "isc_at_high_temp": round(isc_high_temp, 2),
    }


def validate_string_config(modules_per_string, module_spec, inverter_spec, max_ambient_c=45.0):
    """Return True if a given modules-per-string + inverter combo is electrically valid.

    Only error-level issues are considered; warnings and info are ignored.
    """
    dummy_array = {
        "modules_per_string": modules_per_string,
        "strings": 1,
        "module": module_spec.get("name", "unknown"),
        "inverter": inverter_spec.get("name", "unknown"),
    }
    result = validate_array_electrical(dummy_array, module_spec, inverter_spec, max_ambient_c)
    return not any(i["severity"] == "error" for i in result["issues"])


def validate_project_electrical(project):
    """Validate all arrays in a project and return aggregated results."""
    validated = SimulationInput.model_validate(project)
    project = validated.model_dump()
    all_issues = []
    total_dc = 0.0
    total_ac = 0.0
    per_array = []
    for arr in project["arrays"]:
        mod = project["module_specs"][arr["module"]]
        inv = project["inverter_specs"][arr["inverter"]]
        res = validate_array_electrical(arr, mod, inv)
        all_issues.extend(res["issues"])
        total_dc += res["total_dc_w"]
        total_ac += res["inverter_ac_w"]
        per_array.append({
            "name": arr["name"],
            "string_v_max": res["string_v_max"],
            "string_v_min": res["string_v_min"],
            "dc_ac_ratio": res["dc_ac_ratio"],
            "strings": res["strings"],
            "modules_per_string": res["modules_per_string"],
            "total_modules": res["total_modules"],
            "total_dc_w": res["total_dc_w"],
            "issues": res["issues"],
        })

    overall_ratio = total_dc / total_ac if total_ac > 0 else float("inf")
    summary = {
        "total_dc_w": total_dc,
        "total_ac_w": total_ac,
        "overall_dc_ac_ratio": round(overall_ratio, 2),
        "issue_count": len(all_issues),
        "error_count": sum(1 for i in all_issues if i["severity"] == "error"),
        "warning_count": sum(1 for i in all_issues if i["severity"] == "warning"),
    }
    return {"summary": summary, "issues": all_issues, "arrays": per_array}
