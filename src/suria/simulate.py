"""PV simulation engine using pvlib."""
import math
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import pvlib
from pvlib.bifacial.infinite_sheds import get_irradiance
from pvlib.location import Location
from pvlib.modelchain import ModelChain

from suria.domain.simulation_input import SimulationInput
from suria.engine.loss_tree import LossEntry, LossTree
from suria.layout import calculate_row_spacing
from suria.timezone import get_timezone

import warnings

warnings.filterwarnings("ignore")
warnings.filterwarnings("ignore", category=RuntimeWarning, module="scipy.optimize._chandrupatla")

CACHE_DIR = Path(".cache/pvgis")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _pvgis_cache_key(lat, lon):
    """Return cache file path for a lat/lon pair (rounded to 3 decimals ~100 m)."""
    lat_r = round(lat, 3)
    lon_r = round(lon, 3)
    return CACHE_DIR / f"{lat_r}_{lon_r}.pkl"


def _load_cached_weather(lat, lon):
    """Return cached (data, lat, lon, alt) or None."""
    path = _pvgis_cache_key(lat, lon)
    if path.exists():
        try:
            with open(path, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None
    return None


def _save_cached_weather(lat, lon, payload):
    """Cache weather data payload to disk."""
    path = _pvgis_cache_key(lat, lon)
    try:
        with open(path, "wb") as f:
            pickle.dump(payload, f)
    except Exception:
        pass


class WeatherFetchError(Exception):
    """Raised when weather data cannot be retrieved."""
    pass


def get_pvgis_weather(lat, lon):
    """Pull hourly TMY from PVGIS, with file-based caching."""
    cached = _load_cached_weather(lat, lon)
    if cached is not None:
        return cached

    try:
        data, meta = pvlib.iotools.get_pvgis_tmy(
            latitude=lat, longitude=lon, map_variables=True
        )
    except Exception as exc:
        raise WeatherFetchError(
            f"Failed to fetch weather data from PVGIS for lat={lat}, lon={lon}. "
            f"Please check your internet connection and try again. ({exc})"
        ) from exc

    inputs = meta.get("inputs", {}).get("location", {})
    result = (
        data,
        inputs.get("latitude", lat),
        inputs.get("longitude", lon),
        inputs.get("elevation", 0),
    )
    _save_cached_weather(lat, lon, result)
    return result


def build_module_params(mod_spec):
    """Convert ModuleSpec dict to pvlib module_parameters.

    Tries the CEC database first when ``cec_name`` is provided, then falls
    back to a manual parameter build.  The critical improvement over the
    original hard-coded build is that ``N_s`` now comes from the CSV rather
    than being locked to 144.
    """
    cec_name = mod_spec.get("cec_name", "")
    if cec_name:
        try:
            cec_mods = pvlib.pvsystem.retrieve_sam("CECMod")
            params = cec_mods[cec_name].to_dict()
            # Ensure bifacial flag matches our spec
            params["Bifacial"] = 1 if mod_spec.get("bifacial", False) else 0
            params["Bifaciality"] = mod_spec.get("bifaciality", 0.0)
            # Use our dimensions / rated power (CEC may list a slightly
            # different variant)
            params["A_c"] = mod_spec["length"] * mod_spec["width"]
            params["Length"] = mod_spec["length"]
            params["Width"] = mod_spec["width"]
            params["STC"] = mod_spec["p_max"]
            return params
        except Exception:
            pass  # fall through to manual build

    # Manual build for modules not in the CEC database
    n_s = int(mod_spec.get("n_s", 72))
    voc = mod_spec["voc"]
    isc = mod_spec["isc"]
    vmp = mod_spec["vmp"]
    imp = mod_spec["imp"]

    # Improved approximations based on CEC database trends
    # a_ref ≈ N_s * kT/q  (ideality factor ~1 at 298 K)
    k_t_over_q = 0.0257
    a_ref = max(1.5, n_s * k_t_over_q)

    # I_o_ref from the single-diode open-circuit approximation
    # I_L ≈ I_sc (R_sh is large), 0 = I_L - I_o*(exp(V_oc/a)-1) - V_oc/R_sh
    i_o_ref = max(1e-13, isc * math.exp(-voc / a_ref))

    # R_s: typical range 0.15–0.50 Ω for crystalline Si modules
    r_s = max(0.10, min(0.60, (voc - vmp) / imp * 0.25))

    return {
        "name": mod_spec["name"],
        "Technology": "Mono-cSi",
        "Bifacial": 1 if mod_spec.get("bifacial", False) else 0,
        "STC": mod_spec["p_max"],
        "PTC": mod_spec["p_max"] * 0.95,
        "A_c": mod_spec["length"] * mod_spec["width"],
        "Length": mod_spec["length"],
        "Width": mod_spec["width"],
        "N_s": n_s,
        "I_sc_ref": isc,
        "V_oc_ref": voc,
        "I_mp_ref": imp,
        "V_mp_ref": vmp,
        "alpha_sc": mod_spec["temp_coeff_isc"] * isc / 100,
        "beta_oc": mod_spec["temp_coeff_voc"] * voc / 100,
        "a_ref": round(a_ref, 4),
        "I_L_ref": isc,
        "I_o_ref": i_o_ref,
        "R_s": round(r_s, 4),
        "R_sh_ref": 5000.0,
        "Adjust": 8.7,
        "gamma_r": mod_spec["temp_coeff_pmax"],
        "T_NOCT": mod_spec["noct"],
        "Bifaciality": mod_spec.get("bifaciality", 0.0),
    }


def build_inverter_params(inv_spec):
    """Convert InverterSpec dict to pvlib inverter_parameters (Sandia model keys).

    Tries the CEC database first when ``cec_name`` is provided, then falls
    back to a simplified manual build.
    """
    cec_name = inv_spec.get("cec_name", "")
    if cec_name:
        try:
            cec_inv = pvlib.pvsystem.retrieve_sam("cecinverter")
            params = cec_inv[cec_name].to_dict()
            # Ensure efficiency key exists for reporting
            params["efficiency"] = inv_spec.get("efficiency", 0.98)
            return params
        except Exception:
            pass

    return {
        "Paco": inv_spec["p_aco"],
        "Pdco": inv_spec["p_dco"],
        "Vdco": inv_spec["v_dco"],
        "Vdcmax": inv_spec["vdcmax"],
        "Vdcmin": inv_spec["vdcmin"],
        "Pso": 0,
        "Pnt": 0,
        "C0": 0,
        "C1": 0,
        "C2": 0,
        "C3": 0,
        "efficiency": inv_spec.get("efficiency", 0.98),
        "mppt_count": inv_spec.get("mppt_count", 1),
        "mppt_i_max": inv_spec.get("mppt_i_max", 0.0),
        "parallel_strings_max": inv_spec.get("parallel_strings_max", 10),
    }


def _compute_effective_poa(irr_shaded, irr_unshaded, bifaciality):
    """Return effective POA ratio including bifacial rear gain."""
    if bifaciality > 0:
        eff_shaded = irr_shaded["poa_front"] + irr_shaded["poa_back"] * bifaciality
        eff_unshaded = irr_unshaded["poa_front"] + irr_unshaded["poa_back"] * bifaciality
    else:
        eff_shaded = irr_shaded["poa_front"]
        eff_unshaded = irr_unshaded["poa_front"]

    ratio_global = eff_shaded / eff_unshaded
    ratio_direct = irr_shaded["poa_front_direct"] / irr_unshaded["poa_front_direct"]
    ratio_diffuse = irr_shaded["poa_front_diffuse"] / irr_unshaded["poa_front_diffuse"]

    ratio_global = ratio_global.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.0, 1.0)
    ratio_direct = ratio_direct.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.0, 1.0)
    ratio_diffuse = ratio_diffuse.replace([np.inf, -np.inf], np.nan).fillna(1.0).clip(0.0, 1.0)

    return ratio_global, ratio_direct, ratio_diffuse


def simulate_array(site, array, module_params, inverter_params, losses_config=None):
    """Run hourly simulation for one array."""
    if losses_config is None:
        losses_config = {}
    weather, lat, lon, alt = get_pvgis_weather(site["lat"], site["lon"])
    loc = Location(lat, lon, tz=get_timezone(lat, lon, site.get("tz")), altitude=alt)

    # --- Infinite sheds row-to-row shading pre-computation ---
    if array.get("row_spacing_m"):
        row_spacing_m = float(array["row_spacing_m"])
    else:
        row_spacing_m = calculate_row_spacing(array["tilt"], module_params["Width"])
    gcr = module_params["Width"] / row_spacing_m
    height_m = module_params["Width"] / 2.0 * math.sin(math.radians(array["tilt"]))
    albedo = 0.2
    bifaciality = module_params.get("Bifaciality", 0.0)

    solpos = loc.get_solarposition(weather.index)
    dni_extra = pvlib.irradiance.get_extra_radiation(weather.index.dayofyear)

    # Unshaded Perez POA (front side only — used as the base irradiance)
    poa_unshaded = pvlib.irradiance.get_total_irradiance(
        surface_tilt=array["tilt"],
        surface_azimuth=array["azimuth"],
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        dni=weather["dni"],
        ghi=weather["ghi"],
        dhi=weather["dhi"],
        dni_extra=dni_extra,
        model="perez",
    )

    # Isotropic infinite sheds irradiance for shaded and unshaded cases
    irr_shaded = get_irradiance(
        surface_tilt=array["tilt"],
        surface_azimuth=array["azimuth"],
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        gcr=gcr,
        height=height_m,
        pitch=row_spacing_m,
        ghi=weather["ghi"],
        dhi=weather["dhi"],
        dni=weather["dni"],
        albedo=albedo,
    )
    irr_unshaded = get_irradiance(
        surface_tilt=array["tilt"],
        surface_azimuth=array["azimuth"],
        solar_zenith=solpos["apparent_zenith"],
        solar_azimuth=solpos["azimuth"],
        gcr=1e-6,
        height=height_m,
        pitch=row_spacing_m,
        ghi=weather["ghi"],
        dhi=weather["dhi"],
        dni=weather["dni"],
        albedo=albedo,
    )

    ratio_global, ratio_direct, ratio_diffuse = _compute_effective_poa(
        irr_shaded, irr_unshaded, bifaciality
    )

    # Apply ratios to Perez POA
    poa_shaded = pd.DataFrame({
        "poa_global": poa_unshaded["poa_global"] * ratio_global,
        "poa_direct": poa_unshaded["poa_direct"] * ratio_direct,
        "poa_diffuse": poa_unshaded["poa_diffuse"] * ratio_diffuse,
    })

    # Add weather columns required by run_model_from_poa
    poa_unshaded["temp_air"] = weather["temp_air"]
    poa_unshaded["wind_speed"] = weather["wind_speed"]
    poa_shaded["temp_air"] = weather["temp_air"]
    poa_shaded["wind_speed"] = weather["wind_speed"]

    temp_params = pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS["sapm"]["open_rack_glass_glass"]

    system = pvlib.pvsystem.PVSystem(
        arrays=[pvlib.pvsystem.Array(
            mount=pvlib.pvsystem.FixedMount(
                surface_tilt=array["tilt"], surface_azimuth=array["azimuth"]
            ),
            module_parameters=module_params,
            modules_per_string=array["modules_per_string"],
            strings=array["strings"],
            temperature_model_parameters=temp_params,
        )],
        inverter_parameters=inverter_params,
    )

    mc_ideal = ModelChain(system, loc, aoi_model="physical", spectral_model="no_loss")
    mc_ideal.run_model_from_poa(poa_unshaded)

    mc_actual = ModelChain(system, loc, aoi_model="physical", spectral_model="no_loss")
    mc_actual.run_model_from_poa(poa_shaded)

    ideal_ac = float(np.nansum(np.asarray(getattr(mc_ideal.results, "ac", 0)))) / 1000
    actual_ac = float(np.nansum(np.asarray(getattr(mc_actual.results, "ac", 0)))) / 1000

    # Loss waterfall — all values are for reporting only.
    # pvlib's actual_ac already includes: temperature, inverter, clipping, front_shading.
    # We only apply additional losses (soiling, mismatch, wiring, availability, lid, ac_system).

    # Temperature loss (reporting only — pvlib already applied it)
    try:
        cell_temps = getattr(mc_actual.results, "cell_temperature", None)
    except Exception:
        cell_temps = None
    avg_cell_temp = float(np.nanmean(np.asarray(cell_temps))) if cell_temps is not None else 25.0
    temp_loss_pct = abs(module_params["gamma_r"]) * (avg_cell_temp - 25.0)

    # Clipping loss (reporting only — pvlib inverter model already applied it)
    try:
        dc_power = getattr(mc_actual.results, "dc", None)
    except Exception:
        dc_power = None
    ac_rating_kw = inverter_params["Paco"] / 1000 if "Paco" in inverter_params else 0
    if ac_rating_kw > 0 and dc_power is not None:
        clipped = float(np.nansum(np.asarray((dc_power - ac_rating_kw * 1000).clip(lower=0)))) / 1000
        clipping_pct = (clipped / actual_ac * 100) if actual_ac > 0 else 0.0
    else:
        clipping_pct = 0.0

    # Inverter efficiency loss (use manufacturer's rated efficiency)
    inv_eff = inverter_params.get("efficiency", 0.98)
    inv_loss_pct = (1 - inv_eff) * 100

    # Front shading loss (reporting only — pvlib already applied it via shaded POA)
    front_shading = ((ideal_ac - actual_ac) / ideal_ac * 100) if ideal_ac > 0 else 0.0

    # Near-shading / obstruction loss (user-configurable per array)
    shading_loss_pct = float(array.get("shading_loss_pct", 2.0))

    losses = {
        "soiling": losses_config.get("soiling", 2.0),
        "mismatch": losses_config.get("mismatch", 2.0),
        "wiring": losses_config.get("wiring", 1.5),
        "availability": losses_config.get("availability", 1.0),
        "lid": losses_config.get("lid", 1.5),
        "ac_system": losses_config.get("ac_system", 0.5),
        "near_shading": round(shading_loss_pct, 2),
        "temperature": round(temp_loss_pct, 2),
        "clipping": round(clipping_pct, 2),
        "inverter": round(inv_loss_pct, 2),
        "front_shading": round(front_shading, 2),
    }

    # Build a true loss waterfall: apply each loss sequentially and record intermediate values.
    # The order matches HelioScope's waterfall: soiling → mismatch → wiring → availability
    # → lid → ac_system → near_shading.
    # Temperature, clipping, inverter, front_shading are already applied by pvlib in actual_ac.
    waterfall = {"pvlib_output": round(actual_ac, 1)}
    intermediate = actual_ac
    for name, pct in [
        ("soiling", losses["soiling"]),
        ("mismatch", losses["mismatch"]),
        ("wiring", losses["wiring"]),
        ("availability", losses["availability"]),
        ("lid", losses["lid"]),
        ("ac_system", losses["ac_system"]),
        ("near_shading", losses["near_shading"]),
    ]:
        intermediate *= (1 - pct / 100)
        waterfall[name] = round(intermediate, 1)
    annual_ac = intermediate

    monthly = mc_actual.results.ac.resample("ME").sum() / 1000
    monthly_kwh = monthly.values.tolist() if hasattr(monthly, 'values') else list(monthly)

    capacity_kw = array["modules_per_string"] * array["strings"] * module_params["STC"] / 1000
    specific_yield = annual_ac / capacity_kw

    # Performance ratio using POA irradiance directly (sum in W/m² over hours → kWh/m²)
    total_poa_kwh_m2 = float(np.nansum(np.asarray(poa_shaded["poa_global"]))) / 1000
    performance_ratio = 0.0
    if total_poa_kwh_m2 > 0 and capacity_kw > 0:
        performance_ratio = (annual_ac / (total_poa_kwh_m2 * capacity_kw)) * 100

    # Hourly AC output for CSV export (8760 rows)
    hourly_ac = mc_actual.results.ac
    hourly_data = []
    daily_profile = [0.0] * 24
    if hourly_ac is not None:
        for ts, val in hourly_ac.items():
            hourly_data.append({
                "timestamp": ts.isoformat() if hasattr(ts, 'isoformat') else str(ts),
                "ac_power_w": float(val) if not pd.isna(val) else 0.0,
            })
        # Average daily profile (24 hours)
        try:
            grp = hourly_ac.groupby(hourly_ac.index.hour).mean()
            daily_profile = [float(grp.get(h, 0.0)) if not pd.isna(grp.get(h, 0.0)) else 0.0 for h in range(24)]
        except Exception:
            daily_profile = [0.0] * 24

    # Canonical HelioScope-format loss tree (reporting only)
    nameplate_kwh = total_poa_kwh_m2 * capacity_kw if total_poa_kwh_m2 > 0 else 0.0
    loss_tree = LossTree(nameplate_kwh=round(nameplate_kwh, 1))
    loss_tree.soiling = LossEntry(pct=losses["soiling"], energy_lost_kwh=0.0, source="config")
    loss_tree.mismatch = LossEntry(pct=losses["mismatch"], energy_lost_kwh=0.0, source="config")
    loss_tree.dc_wiring = LossEntry(pct=losses["wiring"], energy_lost_kwh=0.0, source="config")
    loss_tree.availability = LossEntry(pct=losses["availability"], energy_lost_kwh=0.0, source="config")
    loss_tree.lid = LossEntry(pct=losses["lid"], energy_lost_kwh=0.0, source="config")
    loss_tree.ac_system = LossEntry(pct=losses["ac_system"], energy_lost_kwh=0.0, source="config")
    loss_tree.temperature = LossEntry(pct=losses["temperature"], energy_lost_kwh=0.0, source="pvlib")
    loss_tree.inverter_clipping = LossEntry(pct=losses["clipping"], energy_lost_kwh=0.0, source="pvlib")
    loss_tree.inverter_efficiency = LossEntry(pct=losses["inverter"], energy_lost_kwh=0.0, source="pvlib")
    loss_tree.front_shading = LossEntry(
        pct=losses["front_shading"] + losses["near_shading"],
        energy_lost_kwh=0.0,
        source="shading_engine",
    )
    loss_tree.compute()

    return {
        "annual_ac_kwh": annual_ac,
        "monthly_ac_kwh": monthly_kwh,
        "specific_yield": specific_yield,
        "performance_ratio": round(performance_ratio, 1),
        "capacity_factor": annual_ac / (capacity_kw * 8760) * 100,
        "losses": losses,
        "raw_ac_kwh": actual_ac,
        "waterfall": waterfall,
        "loss_tree": loss_tree.to_dict(),
        "loss_diagnostic": loss_tree.diagnostic_summary(),
        "hourly_ac": hourly_data,
        "daily_profile": daily_profile,
    }


def simulate_project(project):
    """Simulate all arrays in a project and sum results.

    The incoming dict is validated against SimulationInput before processing.
    """
    validated = SimulationInput.model_validate(project)
    project = validated.model_dump()
    results = []
    for arr in project["arrays"]:
        mod = project["module_specs"][arr["module"]]
        inv = project["inverter_specs"][arr["inverter"]]
        mod_params = build_module_params(mod)
        inv_params = build_inverter_params(inv)
        r = simulate_array(project["site"], arr, mod_params, inv_params, losses_config=project.get("losses"))
        results.append(r)

    total_annual = sum(r["annual_ac_kwh"] for r in results)
    # Sum monthly arrays safely
    monthly_totals = [sum(r["monthly_ac_kwh"][i] for r in results if i < len(r["monthly_ac_kwh"])) for i in range(12)]

    total_capacity = sum(
        arr["modules_per_string"] * arr["strings"] * project["module_specs"][arr["module"]]["p_max"] / 1000
        for arr in project["arrays"]
    )

    # Aggregate losses (capacity-weighted average)
    all_loss_keys = set()
    for r in results:
        all_loss_keys.update(r.get("losses", {}).keys())
    avg_losses = {}
    for key in all_loss_keys:
        weighted_sum = sum(
            r["losses"].get(key, 0) * r["annual_ac_kwh"] for r in results if "losses" in r
        )
        total_weight = sum(r["annual_ac_kwh"] for r in results if "losses" in r)
        avg_losses[key] = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    # Aggregate hourly data across arrays
    hourly_combined = []
    if results and results[0].get("hourly_ac"):
        n = len(results[0]["hourly_ac"])
        for i in range(n):
            ts = results[0]["hourly_ac"][i]["timestamp"]
            total_w = sum(r["hourly_ac"][i]["ac_power_w"] for r in results if i < len(r.get("hourly_ac", [])))
            hourly_combined.append({"timestamp": ts, "ac_power_w": round(total_w, 2)})

    # Aggregate daily profile (sum across arrays, then convert to kW)
    daily_profile = [0.0] * 24
    for r in results:
        prof = r.get("daily_profile", [0.0] * 24)
        for h in range(24):
            daily_profile[h] += prof[h] / 1000  # W → kW

    # Aggregate canonical loss tree (energy-weighted average of pct values)
    loss_tree_keys = [
        "reflection_pct", "soiling_pct", "irradiance_pct", "temperature_pct",
        "mismatch_pct", "dc_wiring_pct", "bifaciality_pct", "front_shading_pct",
        "inverter_clipping_pct", "inverter_efficiency_pct", "ac_system_pct",
    ]
    aggregated_loss_tree = {}
    for key in loss_tree_keys:
        weighted_sum = sum(
            r.get("loss_tree", {}).get(key, 0.0) * r["annual_ac_kwh"] for r in results
        )
        total_weight = sum(r["annual_ac_kwh"] for r in results)
        aggregated_loss_tree[key] = round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0
    aggregated_loss_tree["nameplate_kwh"] = round(
        sum(r.get("loss_tree", {}).get("nameplate_kwh", 0.0) for r in results), 1
    )
    aggregated_loss_tree["grid_kwh"] = round(total_annual, 1)

    return {
        "annual_ac_kwh": total_annual,
        "monthly_ac_kwh": monthly_totals,
        "specific_yield": total_annual / total_capacity,
        "performance_ratio": round(sum(r.get("performance_ratio", 0) * r["annual_ac_kwh"] for r in results) / total_annual, 1) if total_annual > 0 else 0.0,
        "capacity_factor": total_annual / (total_capacity * 8760) * 100,
        "losses": avg_losses,
        "raw_ac_kwh": sum(r.get("raw_ac_kwh", 0) for r in results),
        "loss_tree": aggregated_loss_tree,
        "hourly_ac": hourly_combined,
        "daily_profile": daily_profile,
    }
