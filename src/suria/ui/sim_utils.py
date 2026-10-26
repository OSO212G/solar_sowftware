"""Simulation helpers for the Streamlit UI."""
import streamlit as st

from suria.simulate import simulate_project, WeatherFetchError
from suria.electrical import validate_project_electrical
from suria.nem import validate_nem_sizing
from suria.financials import calculate_financials


def _build_project_dict(modules, inverters):
    """Build a project dict from session state for saving/simulation."""
    mod_specs = {}
    inv_specs = {}
    for arr in st.session_state["arrays"]:
        mod_specs[arr["module"]] = modules[modules["name"] == arr["module"]].iloc[0].to_dict()
        inv_specs[arr["inverter"]] = inverters[inverters["name"] == arr["inverter"]].iloc[0].to_dict()
    return {
        "name": st.session_state["project_name"],
        "customer": st.session_state["customer"],
        "designer": st.session_state["designer"],
        "project_notes": st.session_state.get("project_notes", ""),
        "site": {
            "name": st.session_state["project_name"],
            "lat": st.session_state["site_lat"],
            "lon": st.session_state["site_lon"],
            "altitude": st.session_state["site_altitude"],
        },
        "tariff_block": st.session_state["tariff_block"],
        "consumer_type": st.session_state["consumer_type"],
        "fuse_rating_a": st.session_state["fuse_rating_a"],
        "max_demand_kw": st.session_state["max_demand_kw"],
        "arrays": [
            {
                "name": a["name"],
                "coords": a.get("coords", []),
                "polygon_coords": a.get("coords", []),
                "panel_rectangles": a.get("panel_rectangles", []),
                "tilt": a["tilt"],
                "azimuth": a["azimuth"],
                "modules_per_string": a["modules_per_string"],
                "strings": a["strings"],
                "module": a["module"],
                "inverter": a["inverter"],
                "shading_loss_pct": a.get("shading_loss_pct", 2.0),
                "portrait": a.get("portrait", False),
                "setback_m": a.get("setback_m", 0.5),
                "row_spacing_m": a.get("row_spacing_m", None),
                "keepouts": a.get("keepouts", []),
            }
            for a in st.session_state["arrays"]
        ],
        "module_specs": mod_specs,
        "inverter_specs": inv_specs,
        "solar_atap_export_rate": st.session_state.get("solar_atap_export_rate", 0.25),
        "self_consumption_pct": st.session_state.get("self_consumption_pct", 70) / 100,
        "annual_degradation_pct": st.session_state.get("annual_degradation_pct", 0.5),
        "losses": {
            "soiling": st.session_state.get("loss_soiling", 2.0),
            "mismatch": st.session_state.get("loss_mismatch", 2.0),
            "wiring": st.session_state.get("loss_wiring", 1.5),
            "availability": st.session_state.get("loss_availability", 1.0),
            "lid": st.session_state.get("loss_lid", 1.5),
            "ac_system": st.session_state.get("loss_ac_system", 0.5),
            "near_shading": st.session_state.get("loss_near_shading", 2.0),
        },
    }


def _run_simulation(modules, inverters):
    """Helper to run simulation and advance to results."""
    try:
        with st.spinner("Pulling weather and simulating all arrays..."):
            project = _build_project_dict(modules, inverters)
            mod_specs = project["module_specs"]

            result = simulate_project(project)
            elec = validate_project_electrical(project)
            result["electrical"] = elec

            nem = validate_nem_sizing(
                project,
                consumer_type=project.get("consumer_type", "auto"),
                fuse_rating_a=project.get("fuse_rating_a") or None,
                max_demand_kw=project.get("max_demand_kw") or None,
            )
            result["nem"] = nem

            # Compute financials with defaults for PDF export
            dc_kw = sum(
                a["modules_per_string"] * a["strings"] * mod_specs[a["module"]]["p_max"] / 1000
                for a in st.session_state["arrays"]
            )
            cost_per_kw = float(st.session_state.get("system_cost_per_kw", 3500.0))
            default_cost = dc_kw * cost_per_kw
            fin = calculate_financials(
                result["annual_ac_kwh"],
                default_cost,
                self_consumption_pct=st.session_state.get("self_consumption_pct", 70) / 100,
                tariff_block=st.session_state["tariff_block"],
                export_rate_rm_per_kwh=st.session_state.get("solar_atap_export_rate", 0.25),
                annual_degradation_pct=st.session_state.get("annual_degradation_pct", 0.5),
            )
            result["financials"] = fin
            result["system_cost_rm"] = default_cost

            st.session_state["result"] = result
            st.session_state["project"] = project
            st.session_state["ui_step"] = 3
            st.rerun()
    except WeatherFetchError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"Simulation failed: {exc}")
