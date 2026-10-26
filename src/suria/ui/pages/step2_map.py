"""Step 2: HelioScope-style full-screen map design canvas."""
import json

import folium
import streamlit as st
from streamlit_folium import st_folium

from suria.domain.frame import make_frame
from suria.layout import estimate_panels_from_polygon, calculate_row_spacing
from suria.storage import save_project
from suria.ui.components_loader import load_components
from suria.ui.layout_utils import _relayout_array
from suria.ui.sim_utils import _build_project_dict, _run_simulation
from suria.electrical import validate_array_electrical
from suria.ui.panels.array_config import render_array_config_panel
from suria.ui.panels.keepout import render_keepout_panel
from suria.ui.panels.component_picker import render_component_picker

ARRAY_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"]


def render_step2_map_design():
    """HelioScope-style full-screen design canvas."""
    modules, inverters = load_components()
    lat = st.session_state["site_lat"]
    lon = st.session_state["site_lon"]

    # ── Light top bar ──
    st.markdown(
        f"""
        <style>
        .heliobar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #ffffff;
            border-bottom: 1px solid #ddd;
            padding: 8px 16px;
            margin: -0.5rem -0.5rem 0 -0.5rem;
            height: 44px;
        }}
        .heliobar-brand {{ font-size: 14px; color: #333; font-weight: 600; }}
        .heliobar-brand b {{ color: #f1c40f; }}
        .heliobar-crumb {{ font-size: 12px; color: #888; }}
        </style>
        <div class="heliobar">
            <div class="heliobar-brand">
                <b>Suria</b>
                <span class="heliobar-crumb">/ {st.session_state['project_name']} / Design</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Action buttons (placed right after the bar)
    act1, act2, act3, _ = st.columns([1.2, 1.2, 1.2, 6.4])
    with act1:
        if st.button("Save & Exit", type="primary", use_container_width=True, key="btn_save_exit"):
            project = _build_project_dict(modules, inverters)
            pid = save_project(project)
            st.session_state["project"] = project
            st.session_state["project"]["saved_project_id"] = pid
            st.session_state["selected_array_id"] = None
            st.session_state["ui_step"] = 1
            st.success(f"Project saved (ID: {pid})")
            st.rerun()
    with act2:
        if st.button("Run Sim →", type="secondary", use_container_width=True, key="btn_run_sim"):
            if not st.session_state["arrays"]:
                st.warning("Draw at least one array polygon on the map first.")
            else:
                try:
                    _run_simulation(modules, inverters)
                except Exception as e:
                    msg = str(e)
                    if "HTTP" in msg or "timeout" in msg.lower() or "Connection" in msg:
                        st.error("Weather data could not be loaded. Please check your internet connection and try again.")
                    elif "PVGIS" in msg or "pvgis" in msg.lower():
                        st.error("PVGIS weather service is temporarily unavailable. Please try again in a few minutes.")
                    elif "CEC" in msg or "cec_name" in msg:
                        st.error("A component database lookup failed. Try selecting a different module or inverter.")
                    elif "MPPT" in msg or "voltage" in msg.lower():
                        st.error("Electrical validation failed: string voltage is outside the inverter's MPPT range. Reduce modules per string or choose a different inverter.")
                    else:
                        st.error(f"Simulation failed: {msg}. If this keeps happening, try refreshing the page or checking your design parameters.")
                    import traceback
                    st.caption(f"Technical details: {traceback.format_exc()[:300]}")
    with act3:
        if st.button("← Settings", type="secondary", use_container_width=True, key="btn_settings_top"):
            st.session_state["ui_step"] = 1
            st.rerun()

    # ── Sidebar: floating config panel ──
    with st.sidebar:
        picker_mode = st.session_state.get("picker_mode")
        picker_arr_id = st.session_state.get("picker_array_id")
        selected_id = st.session_state.get("selected_array_id")
        current_mode = st.session_state.get("sidebar_mode", "Mechanical")

        # ── Panel header: Design name + status ──
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
                <span style="font-size:14px;font-weight:600;color:#333;">{st.session_state['project_name']}</span>
                <span style="font-size:10px;color:#888;background:#fff;padding:2px 6px;border-radius:3px;border:1px solid #ddd;">Saved</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # ── Mode tabs ──
        mode_options = ["Mechanical", "Keepouts", "Electrical", "Storage", "Advanced"]
        mode_labels = {"Mechanical": "⚙️", "Keepouts": "🚫", "Electrical": "⚡", "Storage": "🔋", "Advanced": "⋯"}
        new_mode = st.radio(
            "Mode",
            mode_options,
            index=mode_options.index(current_mode) if current_mode in mode_options else 0,
            horizontal=True,
            format_func=lambda x: mode_labels[x],
            label_visibility="collapsed",
            key="sidebar_mode_radio",
        )
        if new_mode != current_mode:
            st.session_state["sidebar_mode"] = new_mode
            st.rerun()
        st.divider()

        if picker_mode and picker_arr_id:
            render_component_picker(picker_mode, picker_arr_id, modules, inverters)
        elif selected_id and current_mode == "Keepouts":
            render_keepout_panel(selected_id)
        elif selected_id:
            render_array_config_panel(selected_id, modules, inverters)
        else:
            if current_mode == "Electrical":
                # Electrical summary mode with per-array details
                if st.session_state["arrays"]:
                    for arr in st.session_state["arrays"]:
                        mod_spec = modules[modules["name"] == arr["module"]].iloc[0].to_dict() if arr["module"] in modules["name"].values else {}
                        inv_spec = inverters[inverters["name"] == arr["inverter"]].iloc[0].to_dict() if arr["inverter"] in inverters["name"].values else {}
                        if not mod_spec or not inv_spec:
                            continue
                        from suria.electrical import validate_array_electrical
                        res = validate_array_electrical(arr, mod_spec, inv_spec)
                        total_panels = arr["modules_per_string"] * arr["strings"]
                        dc_kw = total_panels * mod_spec["p_max"] / 1000
                        st.markdown(
                            f"""
                            <div style="display:flex;align-items:center;gap:8px;margin-bottom:2px;">
                                <span style="width:8px;height:8px;background:#3498db;border-radius:2px;display:inline-block;"></span>
                                <span style="font-size:12px;font-weight:600;color:#333;">{arr['name']}</span>
                            </div>
                            <div style="font-size:11px;color:#666;margin-bottom:2px;">
                                {total_panels} panels | {dc_kw:.2f} kWp DC
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.caption(f"V_oc: {res['string_v_max']:.0f} V  |  V_mp: {res['string_v_min']:.0f} V")
                        issues = res["issues"]
                        if issues:
                            for issue in issues[:2]:
                                if issue["severity"] == "error":
                                    st.error(issue["message"])
                                elif issue["severity"] == "warning":
                                    st.warning(issue["message"])
                                else:
                                    st.info(issue["message"])
                        else:
                            st.success("OK", icon="✓")
                        st.divider()
                else:
                    st.info("No arrays to check.")
            else:
                # ── Mechanical mode: Field Segments list ──
                # System summary
                total_panels_all = sum(a["modules_per_string"] * a["strings"] for a in st.session_state["arrays"])
                total_dc_kw_sidebar = 0.0
                total_ac_kw_sidebar = 0.0
                for a in st.session_state["arrays"]:
                    mod_spec = modules[modules["name"] == a["module"]].iloc[0] if a["module"] in modules["name"].values else None
                    inv_spec = inverters[inverters["name"] == a["inverter"]].iloc[0] if a["inverter"] in inverters["name"].values else None
                    total_dc_kw_sidebar += a["modules_per_string"] * a["strings"] * (mod_spec["p_max"] / 1000) if mod_spec is not None else 0
                    total_ac_kw_sidebar += inv_spec["p_aco"] / 1000 if inv_spec is not None else 0

                if st.session_state["arrays"]:
                    c1, c2 = st.columns(2)
                    c1.metric("Panels", total_panels_all)
                    c2.metric("DC kWp", f"{total_dc_kw_sidebar:.2f}")
                    if total_ac_kw_sidebar > 0:
                        st.caption(f"DC:AC ratio {total_dc_kw_sidebar/total_ac_kw_sidebar:.2f}")
                    st.divider()

                # Field Segments header with + New
                seg_hdr1, seg_hdr2 = st.columns([3, 1])
                with seg_hdr1:
                    st.markdown("""<span style="font-size:11px;color:#666;text-transform:uppercase;letter-spacing:0.5px;">Field Segments</span>""", unsafe_allow_html=True)
                with seg_hdr2:
                    if st.button("+ New", key="btn_new_segment", use_container_width=True):
                        pass

                st.checkbox("Field segments cast shadows", value=True, key="chk_cast_shadows")

                if not st.session_state["arrays"]:
                    st.caption("Add a field segment to get started")
                    st.caption("0 Modules, 0 p")

                selected_id = st.session_state.get("selected_array_id")
                for i, arr in enumerate(st.session_state["arrays"]):
                    total_panels = arr["modules_per_string"] * arr["strings"]
                    color = ARRAY_COLORS[i % len(ARRAY_COLORS)]
                    is_selected = arr["id"] == selected_id
                    # Quick electrical check for icon
                    mod_spec = modules[modules["name"] == arr["module"]].iloc[0].to_dict() if arr["module"] in modules["name"].values else {}
                    inv_spec = inverters[inverters["name"] == arr["inverter"]].iloc[0].to_dict() if arr["inverter"] in inverters["name"].values else {}
                    elec_icon = ""
                    if mod_spec and inv_spec:
                        elec_res = validate_array_electrical(arr, mod_spec, inv_spec)
                        errs = sum(1 for issue in elec_res["issues"] if issue["severity"] == "error")
                        warns = sum(1 for issue in elec_res["issues"] if issue["severity"] == "warning")
                        if errs > 0:
                            elec_icon = " 🔴"
                        elif warns > 0:
                            elec_icon = " 🟡"
                        else:
                            elec_icon = " 🟢"
                    bg_style = "background:#f0f8ff;border-radius:4px;padding:4px 8px;margin:-4px -8px;" if is_selected else ""
                    st.markdown(
                        f"<div style='{bg_style}'><span style='color:{color};'>●</span> <b>{arr['name']}</b> — {total_panels} panels, {arr['tilt']}°{elec_icon}</div>",
                        unsafe_allow_html=True,
                    )
                    c1, c2, c3 = st.columns([1, 1, 1])
                    if c1.button("Edit", key=f"edit_{arr['id']}", use_container_width=True):
                        st.session_state["selected_array_id"] = arr["id"]
                        st.rerun()
                    if c2.button("Dup", key=f"dup_{arr['id']}", use_container_width=True):
                        new_id = st.session_state["next_array_id"]
                        st.session_state["next_array_id"] += 1
                        dup = dict(arr)
                        dup["id"] = new_id
                        dup["name"] = f"{arr['name']} (Copy)"
                        st.session_state["arrays"].append(dup)
                        st.rerun()
                    if c3.button("X", key=f"del_{arr['id']}", use_container_width=True):
                        st.session_state["confirm_delete_array_id"] = arr["id"]
                        st.rerun()

                # Per-array delete confirmation
                if st.session_state.get("confirm_delete_array_id"):
                    del_id = st.session_state["confirm_delete_array_id"]
                    del_arr = next((a for a in st.session_state["arrays"] if a["id"] == del_id), None)
                    if del_arr:
                        st.warning(f"Delete **{del_arr['name']}**?")
                        c_y, c_n = st.columns(2)
                        if c_y.button("Yes", key="btn_conf_del", use_container_width=True):
                            st.session_state["arrays"] = [a for a in st.session_state["arrays"] if a["id"] != del_id]
                            if st.session_state.get("selected_array_id") == del_id:
                                st.session_state["selected_array_id"] = None
                            st.session_state["confirm_delete_array_id"] = None
                            st.rerun()
                        if c_n.button("Cancel", key="btn_cancel_del", use_container_width=True):
                            st.session_state["confirm_delete_array_id"] = None
                            st.rerun()
                    else:
                        st.session_state["confirm_delete_array_id"] = None

                if st.button("Clear All", use_container_width=True):
                    st.session_state["confirm_clear"] = True
                    st.rerun()
                if st.session_state.get("confirm_clear"):
                    st.warning("Delete ALL arrays?")
                    c_y, c_n = st.columns(2)
                    if c_y.button("Yes, clear", key="btn_conf_clear", use_container_width=True):
                        st.session_state["arrays"] = []
                        st.session_state["last_processed_drawing"] = None
                        st.session_state["confirm_clear"] = False
                        st.rerun()
                    if c_n.button("Cancel", key="btn_cancel_clear", use_container_width=True):
                        st.session_state["confirm_clear"] = False
                        st.rerun()

    # ── Main area: Full-width map ──
    all_lats = [lat]
    all_lons = [lon]
    for arr in st.session_state["arrays"]:
        if arr.get("coords"):
            for c in arr["coords"]:
                all_lons.append(c[0])
                all_lats.append(c[1])

    m = folium.Map(
        location=[lat, lon],
        zoom_start=20,
        tiles=None,
        max_zoom=22,
        max_native_zoom=19,
    )
    if len(all_lats) > 1:
        m.fit_bounds([[min(all_lats), min(all_lons)], [max(all_lats), max(all_lons)]], padding=(30, 30))
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri",
        name="Esri Satellite",
        overlay=False,
        control=True,
        max_zoom=22,
        max_native_zoom=19,
    ).add_to(m)
    folium.Marker([lat, lon], tooltip="Site center").add_to(m)

    for i, arr in enumerate(st.session_state["arrays"]):
        color = ARRAY_COLORS[i % len(ARRAY_COLORS)]
        mod_spec = modules[modules["name"] == arr["module"]].iloc[0] if arr["module"] in modules["name"].values else None
        dc_kw = arr["modules_per_string"] * arr["strings"] * (mod_spec["p_max"] / 1000) if mod_spec is not None else 0
        if arr.get("coords"):
            folium_coords = [[c[1], c[0]] for c in arr["coords"]]
            popup_html = (
                f"<b>{arr['name']}</b><br>"
                f"{arr['modules_per_string'] * arr['strings']} panels | {dc_kw:.2f} kWp<br>"
                f"{arr['module']}<br>{arr['inverter']}"
            )
            folium.Polygon(
                locations=folium_coords,
                popup=folium.Popup(popup_html, max_width=200),
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.25,
            ).add_to(m)
            if arr.get("panel_rectangles"):
                for rect in arr["panel_rectangles"]:
                    folium_rect = [[c[1], c[0]] for c in rect]
                    folium.Polygon(
                        locations=folium_rect,
                        color=color,
                        weight=1,
                        fill=True,
                        fill_color=color,
                        fill_opacity=0.4,
                    ).add_to(m)
            # Render keepout polygons in yellow
            for ko in arr.get("keepouts", []):
                if not ko.get("active", True):
                    continue
                ko_coords = ko.get("coords")
                if not ko_coords or len(ko_coords) < 3:
                    continue
                folium_ko = [[c[1], c[0]] for c in ko_coords]
                folium.Polygon(
                    locations=folium_ko,
                    color="#f1c40f",
                    weight=2,
                    fill=True,
                    fill_color="#f1c40f",
                    fill_opacity=0.35,
                ).add_to(m)

    draw = folium.plugins.Draw(
        export=True,
        draw_options={
            "polyline": False,
            "rectangle": True,
            "polygon": True,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True},
    )
    draw.add_to(m)
    folium.LayerControl().add_to(m)

    map_data = st_folium(m, width="100%", height=900, returned_objects=["last_active_drawing"])

    if map_data and map_data.get("last_active_drawing"):
        drawing = map_data["last_active_drawing"]
        drawing_id = json.dumps(drawing, sort_keys=True)
        if drawing_id != st.session_state["last_processed_drawing"]:
            st.session_state["last_processed_drawing"] = drawing_id
            geom = drawing.get("geometry", {})
            if geom.get("type") in ("Polygon", "Rectangle"):
                new_coords = geom["coordinates"][0]
                current_mode = st.session_state.get("sidebar_mode", "Mechanical")
                selected_arr_id = st.session_state.get("selected_array_id")

                if current_mode == "Keepouts" and selected_arr_id is not None:
                    # Add keepout to selected array
                    arr = next((a for a in st.session_state["arrays"] if a["id"] == selected_arr_id), None)
                    if arr is not None:
                        if "keepouts" not in arr:
                            arr["keepouts"] = []
                        next_ko_id = max((ko.get("id", 0) for ko in arr["keepouts"]), default=0) + 1
                        arr["keepouts"].append({
                            "id": next_ko_id,
                            "description": f"Keepout {next_ko_id}",
                            "coords": new_coords,
                            "height_m": 0.0,
                            "active": True,
                        })
                        frame = make_frame(lat, lon)
                        _relayout_array(arr, modules, frame=frame)
                        # Auto-adjust string config to match new panel count
                        count = arr.get("panel_count", 0)
                        if count > 0:
                            mps = arr["modules_per_string"]
                            if mps > count:
                                arr["modules_per_string"] = count
                            arr["strings"] = max(1, count // arr["modules_per_string"])
                        st.rerun()
                elif current_mode == "Keepouts":
                    st.warning("Select an array first, then switch to Keepouts mode to draw obstructions.")
                else:
                    # Create new array (existing behavior)
                    last_arr = st.session_state["arrays"][-1] if st.session_state["arrays"] else {}
                    new_array = {
                        "id": st.session_state["next_array_id"],
                        "name": f"Array {st.session_state['next_array_id']}",
                        "coords": new_coords,
                        "tilt": last_arr.get("tilt", 10),
                        "azimuth": last_arr.get("azimuth", 180),
                        "modules_per_string": last_arr.get("modules_per_string", 20),
                        "strings": 1,
                        "module": last_arr.get("module", modules["name"].iloc[0]),
                        "inverter": last_arr.get("inverter", inverters["name"].iloc[0]),
                        "shading_loss_pct": last_arr.get("shading_loss_pct", 2.0),
                        "portrait": last_arr.get("portrait", False),
                        "setback_m": last_arr.get("setback_m", 0.5),
                    }
                    # Inherit row_spacing_m only if last array had an explicit override
                    inherited_spacing = last_arr.get("row_spacing_m")
                    if inherited_spacing is not None:
                        new_array["row_spacing_m"] = inherited_spacing
                    layout_mod = modules[modules["name"] == new_array["module"]].iloc[0]
                    panel_l = layout_mod["length"]
                    panel_w = layout_mod["width"]
                    portrait = new_array["portrait"]
                    panel_height = panel_l if portrait else panel_w
                    spacing = calculate_row_spacing(new_array["tilt"], panel_height)
                    frame = make_frame(lat, lon)
                    count, centers, rectangles = estimate_panels_from_polygon(
                        new_coords, panel_l, panel_w, spacing, setback_m=new_array["setback_m"], portrait=portrait, azimuth=new_array["azimuth"], frame=frame
                    )
                    new_array["panel_rectangles"] = rectangles
                    new_array["panel_count"] = count
                    if count > 0:
                        new_array["modules_per_string"] = min(20, count)
                        new_array["strings"] = max(1, count // new_array["modules_per_string"])
                    st.session_state["arrays"].append(new_array)
                    st.session_state["next_array_id"] += 1
                    st.session_state["selected_array_id"] = new_array["id"]
                    st.rerun()
