"""Streamlit session-state management and defaults."""

import streamlit as st


def init_session():
    """Set up session-state defaults."""
    defaults = {
        "arrays": [],
        "next_array_id": 1,
        "result": None,
        "project": None,
        "last_processed_drawing": None,
        "ui_step": 1,
        "project_name": "Site A",
        "customer": "",
        "designer": "",
        "site_lat": 3.14,
        "site_lon": 101.69,
        "site_altitude": 50,
        "consumer_type": "auto",
        "fuse_rating_a": 0.0,
        "max_demand_kw": 0.0,
        "system_cost_per_kw": 3500.0,
        "tariff_block": "E1",
        "selected_array_id": None,
        "picker_mode": None,
        "picker_array_id": None,
        "confirm_clear": False,
        "confirm_delete_array_id": None,
        "project_notes": "",
        "sidebar_mode": "Mechanical",
        "loss_soiling": 2.0,
        "loss_mismatch": 2.0,
        "loss_wiring": 1.5,
        "loss_availability": 1.0,
        "loss_lid": 1.5,
        "loss_ac_system": 0.5,
        "loss_near_shading": 2.0,
        "solar_atap_export_rate": 0.25,
        "self_consumption_pct": 70,
        "annual_degradation_pct": 0.5,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val
