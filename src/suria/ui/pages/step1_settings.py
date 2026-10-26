"""Step 1: Project settings form."""
import streamlit as st

from suria.geocode import geocode_address, lookup_altitude
from suria.importers import import_geojson, import_kml
from suria.storage import delete_project, list_projects, load_project, save_project
from suria.ui.components_loader import load_components


def render_step1_project_settings():
    """Step 1: Project settings form."""
    st.header("Project Settings")
    st.caption("Enter project details and site location before moving to the map.")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state["project_name"] = st.text_input(
            "Project name", value=st.session_state["project_name"]
        )
        st.session_state["customer"] = st.text_input(
            "Customer", value=st.session_state["customer"]
        )
    with c2:
        st.session_state["designer"] = st.text_input(
            "Designer", value=st.session_state["designer"]
        )
        st.session_state["site_altitude"] = st.number_input(
            "Altitude (m)", value=int(st.session_state["site_altitude"])
        )
    with c3:
        st.session_state["site_lat"] = st.number_input(
            "Latitude", value=st.session_state["site_lat"], format="%.6f"
        )
        st.session_state["site_lon"] = st.number_input(
            "Longitude", value=st.session_state["site_lon"], format="%.6f"
        )

    st.session_state["project_notes"] = st.text_area(
        "Project notes",
        value=st.session_state["project_notes"],
        placeholder="Site conditions, customer requirements, special considerations...",
        height=80,
    )

    cost_col, preset_col = st.columns([1, 1])
    with cost_col:
        st.session_state["system_cost_per_kw"] = st.number_input(
            "System cost (RM/kW)", value=float(st.session_state.get("system_cost_per_kw", 3500.0)),
            step=100.0, format="%.0f",
            help="Used for payback calculation. Typical range RM 3,000–4,500/kW.",
        )
    with preset_col:
        st.write("")
        st.write("")
        preset = st.selectbox(
            "Project Preset", ["Custom", "Residential", "Commercial / Industrial"],
            help="Auto-fills typical defaults for the project type.",
        )
        if st.button("Apply Preset", use_container_width=True) and preset != "Custom":
            if preset == "Residential":
                st.session_state["consumer_type"] = "auto"
                st.session_state["tariff_block"] = "A"
                st.session_state["system_cost_per_kw"] = 4000.0
                st.session_state["solar_atap_export_rate"] = 0.25
                st.session_state["loss_soiling"] = 2.0
                st.session_state["loss_mismatch"] = 2.0
                st.session_state["loss_wiring"] = 1.5
                st.session_state["loss_availability"] = 1.0
                st.session_state["loss_lid"] = 1.5
                st.session_state["loss_ac_system"] = 0.5
            elif preset == "Commercial / Industrial":
                st.session_state["consumer_type"] = "commercial_lv"
                st.session_state["tariff_block"] = "E1"
                st.session_state["system_cost_per_kw"] = 3500.0
                st.session_state["solar_atap_export_rate"] = 0.25
                st.session_state["loss_soiling"] = 3.0
                st.session_state["loss_mismatch"] = 2.0
                st.session_state["loss_wiring"] = 1.5
                st.session_state["loss_availability"] = 1.0
                st.session_state["loss_lid"] = 1.5
                st.session_state["loss_ac_system"] = 0.5
            st.rerun()

    # Address search
    addr_col1, addr_col2 = st.columns([3, 1])
    with addr_col1:
        address_query = st.text_input(
            "Search address", placeholder="e.g. Kuala Lumpur, Malaysia",
            key="address_search"
        )
    with addr_col2:
        st.write("")
        st.write("")
        if st.button("Find", use_container_width=True, key="btn_geocode"):
            if address_query.strip():
                result = geocode_address(address_query.strip())
                if result:
                    lat, lon, name = result
                    st.session_state["site_lat"] = round(lat, 6)
                    st.session_state["site_lon"] = round(lon, 6)
                    alt = lookup_altitude(lat, lon)
                    if alt is not None:
                        st.session_state["site_altitude"] = alt
                    st.success(f"Found: {name}")
                    st.rerun()
                else:
                    st.error("Address not found. Try a more specific query.")
            else:
                st.warning("Enter an address first.")

    st.divider()

    st.subheader("Import Polygons")
    uploaded = st.file_uploader("Upload KML or GeoJSON", type=["kml", "geojson"])
    if uploaded is not None:
        from pathlib import Path
        suffix = Path(uploaded.name).suffix.lower()
        tmp_path = Path("__tmp_import" + suffix)
        tmp_path.write_bytes(uploaded.getvalue())
        try:
            if suffix == ".geojson":
                polygons = import_geojson(tmp_path)
            else:
                polygons = import_kml(tmp_path)
            if not polygons:
                st.warning("No polygons found in the uploaded file.")
            else:
                modules, inverters = load_components()
                demo_mod = modules["name"].iloc[0]
                demo_inv = inverters["name"].iloc[0]
                next_id = st.session_state.get("next_array_id", 1)
                for poly in polygons:
                    st.session_state["arrays"].append({
                        "id": next_id,
                        "name": poly["name"] or f"Array {next_id}",
                        "coords": poly["coords"],
                        "tilt": 10,
                        "azimuth": 180,
                        "modules_per_string": 20,
                        "strings": 1,
                        "module": demo_mod,
                        "inverter": demo_inv,
                        "shading_loss_pct": 2.0,
                        "portrait": False,
                        "setback_m": 0.5,
                    })
                    next_id += 1
                st.session_state["next_array_id"] = next_id
                st.success(f"Imported {len(polygons)} polygon(s). Go to Map Design to view.")
        except Exception as e:
            st.error(f"Import failed: {e}")
        finally:
            tmp_path.unlink(missing_ok=True)

    st.divider()

    st.subheader("Solar ATAP / Tariff Settings")
    ct1, ct2, ct3 = st.columns(3)
    with ct1:
        st.session_state["consumer_type"] = st.selectbox(
            "Consumer Type",
            ["auto", "domestic", "commercial_lv", "commercial_mv"],
            index=["auto", "domestic", "commercial_lv", "commercial_mv"].index(st.session_state["consumer_type"]),
            help="Auto detects from tariff block. Domestic = residential; Commercial LV/MV = business/industrial.",
        )
    with ct2:
        st.session_state["fuse_rating_a"] = st.number_input(
            "Fuse Rating (A)", value=float(st.session_state["fuse_rating_a"]), step=10.0,
            help="Leave 0 to use typical default for the tariff block. Only used for domestic NEM sizing.",
        )
    with ct3:
        st.session_state["max_demand_kw"] = st.number_input(
            "Max Demand (kW)", value=float(st.session_state["max_demand_kw"]), step=50.0,
            help="Leave 0 to ignore. Used for commercial NEM sizing (75% of max demand limit).",
        )
    st.session_state["tariff_block"] = st.selectbox(
        "TNB Tariff Block", ["A", "B", "C", "D", "E1", "E2"],
        index=["A", "B", "C", "D", "E1", "E2"].index(st.session_state["tariff_block"]),
    )
    st.caption("Tariff block determines TNB rates and Solar ATAP consumer category when set to Auto.")

    export_col, self_con_col = st.columns([1, 1])
    with export_col:
        st.session_state["solar_atap_export_rate"] = st.number_input(
            "Solar ATAP export rate (RM/kWh)",
            value=float(st.session_state["solar_atap_export_rate"]),
            min_value=0.0, max_value=1.0, step=0.01, format="%.2f",
            help="Rate TNB pays for exported solar energy. Default 0.25 RM/kWh. Verify with current TNB schedule.",
        )
    with self_con_col:
        st.session_state["self_consumption_pct"] = st.slider(
            "Self-consumption %", 0, 100, int(st.session_state["self_consumption_pct"]),
            help="Percentage of solar energy used on-site vs exported. Typical: 70% commercial, 80% residential.",
        )

    deg_col, _ = st.columns([1, 3])
    with deg_col:
        st.session_state["annual_degradation_pct"] = st.number_input(
            "Annual degradation (%)", 0.0, 5.0, float(st.session_state["annual_degradation_pct"]), step=0.1, format="%.1f",
            help="Year-on-year power drop. Typical: 0.5% for mono PERC, 0.4% for TOPCon.",
        )

    st.divider()

    with st.expander("Loss Assumptions", expanded=False):
        st.caption("Adjust default loss percentages applied to every array in the project.")
        l1, l2, l3 = st.columns(3)
        with l1:
            st.session_state["loss_soiling"] = st.number_input(
                "Soiling (%)", 0.0, 20.0, float(st.session_state["loss_soiling"]), step=0.5,
                help="Dust, dirt, and bird droppings. Typical: 2–5% in urban/tropical areas.",
            )
            st.session_state["loss_mismatch"] = st.number_input(
                "Mismatch (%)", 0.0, 20.0, float(st.session_state["loss_mismatch"]), step=0.5,
                help="Module-to-module variance in current/voltage. Typical: 2%.",
            )
        with l2:
            st.session_state["loss_wiring"] = st.number_input(
                "DC Wiring (%)", 0.0, 20.0, float(st.session_state["loss_wiring"]), step=0.5,
                help="Voltage drop in DC cables. Typical: 1–2%.",
            )
            st.session_state["loss_availability"] = st.number_input(
                "Availability (%)", 0.0, 20.0, float(st.session_state["loss_availability"]), step=0.5,
                help="Downtime from faults, maintenance, grid outages. Typical: 1%.",
            )
        with l3:
            st.session_state["loss_lid"] = st.number_input(
                "LID — Light Induced Degradation (%)", 0.0, 20.0, float(st.session_state["loss_lid"]), step=0.5,
                help="First-year power drop from light exposure. Typical: 1.5% for mono PERC.",
            )
            st.session_state["loss_ac_system"] = st.number_input(
                "AC System (%)", 0.0, 20.0, float(st.session_state["loss_ac_system"]), step=0.5,
                help="AC cable and transformer losses. Typical: 0.5–1%.",
            )

    st.divider()

    col_back, col_next = st.columns([1, 1])
    with col_next:
        if st.button("Next: Map Design →", type="primary", use_container_width=True):
            st.session_state["ui_step"] = 2
            st.rerun()

    # Saved projects quick-load
    st.subheader("Saved Projects")
    projects = list_projects()
    if not projects:
        st.info("No saved projects yet.")
        if st.button("Load Demo Project", type="primary", use_container_width=True):
            # Demo: Petronas Twin Towers area, 2 arrays
            modules, inverters = load_components()
            demo_mod = modules["name"].iloc[0]
            demo_inv = inverters["name"].iloc[0]
            st.session_state["project_name"] = "Demo — KLCC"
            st.session_state["customer"] = "Demo Customer"
            st.session_state["designer"] = "Suria"
            st.session_state["site_lat"] = 3.1588
            st.session_state["site_lon"] = 101.7137
            st.session_state["site_altitude"] = 50
            st.session_state["system_cost_per_kw"] = 3500.0
            st.session_state["tariff_block"] = "E1"
            st.session_state["consumer_type"] = "auto"
            st.session_state["arrays"] = [
                {
                    "id": 1,
                    "name": "Array 1 (South Roof)",
                    "coords": [[101.7135, 3.1586], [101.7139, 3.1586], [101.7139, 3.1590], [101.7135, 3.1590], [101.7135, 3.1586]],
                    "tilt": 10,
                    "azimuth": 180,
                    "modules_per_string": 20,
                    "strings": 5,
                    "module": demo_mod,
                    "inverter": demo_inv,
                    "shading_loss_pct": 2.0,
                    "portrait": False,
                    "setback_m": 0.5,
                },
                {
                    "id": 2,
                    "name": "Array 2 (East Roof)",
                    "coords": [[101.7140, 3.1586], [101.7144, 3.1586], [101.7144, 3.1590], [101.7140, 3.1590], [101.7140, 3.1586]],
                    "tilt": 10,
                    "azimuth": 90,
                    "modules_per_string": 20,
                    "strings": 3,
                    "module": demo_mod,
                    "inverter": demo_inv,
                    "shading_loss_pct": 2.0,
                    "portrait": False,
                    "setback_m": 0.5,
                },
            ]
            st.session_state["next_array_id"] = 3
            st.session_state["result"] = None
            st.session_state["ui_step"] = 2
            st.success("Demo project loaded! Go to Map Design to see the arrays.")
            st.rerun()
    else:
        for p in projects:
            cols = st.columns([3, 2, 1, 1])
            cols[0].write(p["name"])
            cols[1].write(p["created_at"][:10])
            if cols[2].button("Load", key=f"load_{p['id']}"):
                data = load_project(p["id"])
                st.session_state["project"] = data
                st.session_state["project_name"] = data["name"]
                st.session_state["customer"] = data.get("customer", "")
                st.session_state["designer"] = data.get("designer", "")
                st.session_state["project_notes"] = data.get("project_notes", "")
                site = data.get("site", {})
                st.session_state["site_lat"] = site.get("lat", 3.14)
                st.session_state["site_lon"] = site.get("lon", 101.69)
                st.session_state["site_altitude"] = site.get("altitude", 50)
                st.session_state["consumer_type"] = data.get("consumer_type", "auto")
                st.session_state["fuse_rating_a"] = data.get("fuse_rating_a", 0.0)
                st.session_state["max_demand_kw"] = data.get("max_demand_kw", 0.0)
                st.session_state["tariff_block"] = data.get("tariff_block", "E1")
                losses = data.get("losses", {})
                st.session_state["loss_soiling"] = losses.get("soiling", 2.0)
                st.session_state["loss_mismatch"] = losses.get("mismatch", 2.0)
                st.session_state["loss_wiring"] = losses.get("wiring", 1.5)
                st.session_state["loss_availability"] = losses.get("availability", 1.0)
                st.session_state["loss_lid"] = losses.get("lid", 1.5)
                st.session_state["loss_ac_system"] = losses.get("ac_system", 0.5)
                st.session_state["loss_near_shading"] = losses.get("near_shading", 2.0)
                st.session_state["solar_atap_export_rate"] = data.get("solar_atap_export_rate", 0.25)
                st.session_state["self_consumption_pct"] = int(data.get("self_consumption_pct", 0.70) * 100)
                st.session_state["annual_degradation_pct"] = data.get("annual_degradation_pct", 0.5)
                st.session_state["arrays"] = [
                    {
                        "id": i + 1,
                        "name": a["name"],
                        "coords": a.get("polygon_coords", []),
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
                    for i, a in enumerate(data.get("arrays", []))
                ]
                st.session_state["next_array_id"] = len(st.session_state["arrays"]) + 1
                st.session_state["result"] = None
                st.session_state["ui_step"] = 2
                st.session_state["project"] = data
                st.session_state["project"]["saved_project_id"] = p["id"]
                st.success(f"Loaded {data['name']}")
                st.rerun()
            if cols[3].button("Delete", key=f"del_{p['id']}"):
                delete_project(p["id"])
                st.success("Deleted")
                st.rerun()
