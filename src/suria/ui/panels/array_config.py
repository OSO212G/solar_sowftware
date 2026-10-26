"""Array configuration panel for the sidebar."""
import math

import streamlit as st

from suria.domain.frame import make_frame
from suria.electrical import validate_array_electrical
from suria.layout import calculate_row_spacing, polygon_area_m2
from suria.ui.layout_utils import _relayout_array


def render_array_config_panel(arr_id, modules, inverters):
    """HelioScope-style floating panel for array config."""
    arr = next((a for a in st.session_state["arrays"] if a["id"] == arr_id), None)
    if not arr:
        st.error("Array not found.")
        return

    # --- Panel header: back + duplicate + delete ---
    hdr1, hdr2, hdr3 = st.columns([3, 1, 1])
    with hdr1:
        if st.button("← back to list", key=f"cfg_back_{arr_id}", use_container_width=True):
            st.session_state["selected_array_id"] = None
            st.rerun()
    with hdr2:
        if st.button("⧉", key=f"cfg_dup_{arr_id}", use_container_width=True):
            new_id = st.session_state["next_array_id"]
            st.session_state["next_array_id"] += 1
            dup = {k: v for k, v in arr.items()}
            dup["id"] = new_id
            dup["name"] = f"{arr['name']} Copy"
            st.session_state["arrays"].append(dup)
            st.session_state["selected_array_id"] = new_id
            st.rerun()
    with hdr3:
        if st.button("🗑️", key=f"cfg_del_{arr_id}", use_container_width=True):
            st.session_state["arrays"] = [a for a in st.session_state["arrays"] if a["id"] != arr_id]
            st.session_state["selected_array_id"] = None
            st.rerun()

    # --- Live summary ---
    total_panels = arr["modules_per_string"] * arr["strings"]
    layout_count = arr.get("panel_count", 0)
    if arr.get("coords"):
        first = arr["coords"][0]
        frame = make_frame(first[1], first[0])
        area_m2 = polygon_area_m2(arr["coords"], frame=frame)
    else:
        area_m2 = 0.0
    mod_spec = modules[modules["name"] == arr["module"]].iloc[0] if arr["module"] in modules["name"].values else None
    dc_kw = total_panels * (mod_spec["p_max"] / 1000) if mod_spec is not None else 0.0

    st.markdown(
        f"""
        <div style="font-size:12px;font-weight:600;color:#333;margin-bottom:2px;">
            {arr['name']}
        </div>
        <div style="font-size:11px;color:#666;margin-bottom:10px;">
            Modules: <b>{total_panels}</b> ({dc_kw:.2f} kW) · Area: {area_m2:.1f} m²
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Warn if string config doesn't match layout panel count
    if layout_count > 0 and total_panels != layout_count:
        diff = layout_count - total_panels
        if diff > 0:
            st.info(f"Layout has {layout_count} panels but only {total_panels} are strung. {diff} panel(s) unconnected.")
        else:
            st.error(f"String config exceeds layout: {total_panels} strung vs {layout_count} panels available. Strings were auto-capped.")

    # --- Description ---
    new_desc = st.text_input("Description", value=arr.get("description", arr["name"]), key=f"cfg_desc_{arr_id}")
    if new_desc != arr.get("description", arr["name"]):
        arr["description"] = new_desc

    # --- Module picker (label + [...]) ---
    mod_col1, mod_col2 = st.columns([4, 1])
    with mod_col1:
        st.text_input("Module", value=arr["module"], disabled=True, key=f"cfg_mod_label_{arr_id}")
    with mod_col2:
        if st.button("[...]", key=f"cfg_mod_pick_{arr_id}", use_container_width=True):
            st.session_state["picker_mode"] = "module"
            st.session_state["picker_array_id"] = arr_id
            st.rerun()

    # --- Racking ---
    racking_opts = ["Fixed-tilt Racking", "Flush Mount Racking", "Ground-mount Racking"]
    current_racking = arr.get("racking", "Fixed-tilt Racking")
    new_racking = st.selectbox("Racking", racking_opts, index=racking_opts.index(current_racking) if current_racking in racking_opts else 0, key=f"cfg_rack_{arr_id}")
    if new_racking != arr.get("racking", "Fixed-tilt Racking"):
        arr["racking"] = new_racking

    # --- Surface Height, Azimuth, Tilt ---
    c1, c2 = st.columns(2)
    with c1:
        new_height = st.number_input("Surface Height (m)", 0.0, 100.0, float(arr.get("surface_height_m", 0.0)), step=0.5, key=f"cfg_height_{arr_id}")
        if new_height != arr.get("surface_height_m", 0.0):
            arr["surface_height_m"] = new_height
    with c2:
        new_azimuth = st.number_input("Azimuth (°)", 0, 360, int(arr["azimuth"]), key=f"cfg_az_{arr_id}")
        if new_azimuth != arr["azimuth"]:
            arr["azimuth"] = new_azimuth
            arr.pop("row_spacing_m", None)
            _relayout_array(arr, modules)
            st.rerun()

    new_tilt = st.number_input("Tilt (°)", 0, 45, int(arr["tilt"]), key=f"cfg_tilt_{arr_id}")
    if new_tilt != arr["tilt"]:
        arr["tilt"] = new_tilt
        arr.pop("row_spacing_m", None)
        _relayout_array(arr, modules)
        st.rerun()

    # --- Manual Module Controls section ---
    st.markdown('<div class="heliosection">Manual Module Controls</div>', unsafe_allow_html=True)

    orient_opts = ["Landscape (Horizontal)", "Portrait (Vertical)"]
    current_orient = "Portrait (Vertical)" if arr.get("portrait") else "Landscape (Horizontal)"
    o1, o2, o3 = st.columns([3, 1, 1])
    with o1:
        new_orient = st.selectbox("Orientation", orient_opts, index=orient_opts.index(current_orient), key=f"cfg_orient_{arr_id}", label_visibility="collapsed")
    with o2:
        if st.button("↻", key=f"cfg_rot_cw_{arr_id}", use_container_width=True):
            arr["portrait"] = not arr.get("portrait", False)
            arr.pop("row_spacing_m", None)
            _relayout_array(arr, modules)
            st.rerun()
    with o3:
        if st.button("↺", key=f"cfg_rot_ccw_{arr_id}", use_container_width=True):
            arr["portrait"] = not arr.get("portrait", False)
            arr.pop("row_spacing_m", None)
            _relayout_array(arr, modules)
            st.rerun()

    new_portrait = (new_orient == "Portrait (Vertical)")
    if new_portrait != arr.get("portrait", False):
        arr["portrait"] = new_portrait
        arr.pop("row_spacing_m", None)
        _relayout_array(arr, modules)
        st.rerun()

    # --- Automatic Layout Rules section ---
    st.markdown('<div class="heliosection">Automatic Layout Rules</div>', unsafe_allow_html=True)

    mod_row = modules[modules["name"] == arr["module"]].iloc[0]
    panel_l = mod_row["length"]
    panel_w = mod_row["width"]
    portrait = arr.get("portrait", False)
    panel_height = panel_l if portrait else panel_w
    default_spacing = calculate_row_spacing(arr["tilt"], panel_height)

    # Frame Size (up | wide)
    f1, f2 = st.columns(2)
    with f1:
        new_frame_up = st.number_input("Frame up", 1, 10, int(arr.get("frame_up", 1)), key=f"cfg_fup_{arr_id}")
        if new_frame_up != arr.get("frame_up", 1):
            arr["frame_up"] = new_frame_up
    with f2:
        new_frame_wide = st.number_input("Frame wide", 1, 10, int(arr.get("frame_wide", 1)), key=f"cfg_fwide_{arr_id}")
        if new_frame_wide != arr.get("frame_wide", 1):
            arr["frame_wide"] = new_frame_wide

    # Default Orientation (layout-level, for auto-fill)
    layout_orient_opts = ["Landscape (Horizontal)", "Portrait (Vertical)"]
    current_layout_orient = "Portrait (Vertical)" if arr.get("layout_portrait") else "Landscape (Horizontal)"
    new_layout_orient = st.selectbox("Default Orientation", layout_orient_opts, index=layout_orient_opts.index(current_layout_orient), key=f"cfg_def_orient_{arr_id}")
    if (new_layout_orient == "Portrait (Vertical)") != arr.get("layout_portrait", False):
        arr["layout_portrait"] = (new_layout_orient == "Portrait (Vertical)")
        _relayout_array(arr, modules)
        st.rerun()

    # Row Spacing, Module Spacing, Frame Spacing, Setback
    s1, s2 = st.columns(2)
    with s1:
        new_row_spacing = st.number_input("Row Spacing (m)", 0.5, 20.0, float(arr.get("row_spacing_m", default_spacing)), step=0.1, key=f"cfg_rowsp_{arr_id}")
    with s2:
        new_mod_spacing = st.number_input("Module Spacing (m)", 0.0, 5.0, float(arr.get("module_spacing_m", 0.0)), step=0.05, key=f"cfg_modsp_{arr_id}")

    s3, s4 = st.columns(2)
    with s3:
        new_frame_spacing = st.number_input("Frame Spacing (m)", 0.0, 5.0, float(arr.get("frame_spacing_m", 0.0)), step=0.05, key=f"cfg_framesp_{arr_id}")
    with s4:
        new_setback = st.number_input("Setback (m)", 0.0, 5.0, float(arr.get("setback_m", 0.5)), step=0.1, key=f"cfg_setback_{arr_id}")

    spacing_changed = False
    if abs(new_row_spacing - arr.get("row_spacing_m", default_spacing)) > 0.001:
        arr["row_spacing_m"] = new_row_spacing
        spacing_changed = True
    if abs(new_mod_spacing - arr.get("module_spacing_m", 0.0)) > 0.001:
        arr["module_spacing_m"] = new_mod_spacing
        spacing_changed = True
    if abs(new_frame_spacing - arr.get("frame_spacing_m", 0.0)) > 0.001:
        arr["frame_spacing_m"] = new_frame_spacing
        spacing_changed = True
    if abs(new_setback - arr.get("setback_m", 0.5)) > 0.001:
        arr["setback_m"] = new_setback
        spacing_changed = True
    if spacing_changed:
        _relayout_array(arr, modules)
        st.rerun()

    # Alignment icon buttons
    align_opts = ["⬅️", "⏺️", "➡️", "↔️"]
    a1, a2, a3, a4 = st.columns(4)
    with a1:
        if st.button("⬅️", key=f"cfg_al_l_{arr_id}", use_container_width=True):
            arr["alignment"] = "left"
    with a2:
        if st.button("⏺️", key=f"cfg_al_c_{arr_id}", use_container_width=True):
            arr["alignment"] = "center"
    with a3:
        if st.button("➡️", key=f"cfg_al_r_{arr_id}", use_container_width=True):
            arr["alignment"] = "right"
    with a4:
        if st.button("↔️", key=f"cfg_al_j_{arr_id}", use_container_width=True):
            arr["alignment"] = "justify"

    # --- Stringing section ---
    st.markdown('<div class="heliosection">Stringing</div>', unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        new_mps = st.number_input("Modules / String", 1, 100, int(arr["modules_per_string"]), key=f"cfg_mps_{arr_id}")
    with c6:
        new_strings = st.number_input("Strings", 1, 1000, int(arr["strings"]), key=f"cfg_str_{arr_id}")
    if new_mps != arr["modules_per_string"]:
        arr["modules_per_string"] = new_mps
    if new_strings != arr["strings"]:
        arr["strings"] = new_strings

    # --- Shading ---
    new_shade = st.slider(
        "Near-shading loss (%)", 0.0, 30.0,
        float(arr.get("shading_loss_pct", 2.0)), step=0.5,
        key=f"cfg_shade_{arr_id}",
    )
    if new_shade != arr.get("shading_loss_pct", 2.0):
        arr["shading_loss_pct"] = new_shade

    # --- Electrical preview ---
    with st.expander("String Voltage Check"):
        mod_spec = modules[modules["name"] == arr["module"]].iloc[0].to_dict() if arr["module"] in modules["name"].values else {}
        inv_spec = inverters[inverters["name"] == arr["inverter"]].iloc[0].to_dict() if arr["inverter"] in inverters["name"].values else {}
        if mod_spec and inv_spec:
            res = validate_array_electrical(arr, mod_spec, inv_spec)
            st.write(f"String V_oc max (15°C): **{res['string_v_max']:.1f} V**  |  Inverter Vdcmax: **{inv_spec.get('vdcmax', '—')} V**")
            st.write(f"String V_mp min (80°C cell): **{res['string_v_min']:.1f} V**  |  MPPT min: **{inv_spec.get('mppt_min', '—')} V**")
            st.write(f"DC:AC ratio: **{res['dc_ac_ratio']:.2f}**")
            # MPPT capacity details
            mppt_count = inv_spec.get("mppt_count", 1)
            parallel_max = inv_spec.get("parallel_strings_max", 10)
            mppt_i_max = inv_spec.get("mppt_i_max", 0.0)
            strings = arr["strings"]
            strings_per_mppt = math.ceil(strings / mppt_count) if mppt_count > 0 else strings
            parallel_current = res.get("isc_at_high_temp", mod_spec.get("isc", 0)) * strings_per_mppt
            st.write(f"MPPTs: {mppt_count}  |  Strings: {strings} / {mppt_count * parallel_max} max  |  Per-MPPT current: {parallel_current:.1f} A / {mppt_i_max:.1f} A max")
            for issue in res["issues"][:3]:
                if issue["severity"] == "error":
                    st.error(issue["message"])
                elif issue["severity"] == "warning":
                    st.warning(issue["message"])
                else:
                    st.info(issue["message"])
            if not res["issues"]:
                st.success("No electrical issues for this array.")
        else:
            st.info("Select a module and inverter to see voltage check.")
