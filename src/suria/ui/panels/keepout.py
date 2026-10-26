"""Keepout management panel for the sidebar."""
import streamlit as st

from suria.ui.components_loader import load_components
from suria.ui.layout_utils import _relayout_array


def render_keepout_panel(arr_id):
    """HelioScope-style keepout management for an array."""
    arr = next((a for a in st.session_state["arrays"] if a["id"] == arr_id), None)
    if not arr:
        st.error("Array not found.")
        return

    # ── Header: back + array name ──
    hdr1, hdr2 = st.columns([3, 1])
    with hdr1:
        if st.button("← back to list", key=f"ko_back_{arr_id}", use_container_width=True):
            st.session_state["selected_array_id"] = None
            st.rerun()
    with hdr2:
        if st.button("🗑️", key=f"ko_del_arr_{arr_id}", use_container_width=True):
            st.session_state["arrays"] = [a for a in st.session_state["arrays"] if a["id"] != arr_id]
            st.session_state["selected_array_id"] = None
            st.rerun()

    st.markdown(
        f"""<div style="font-size:12px;font-weight:600;color:#333;margin-bottom:10px;">{arr['name']} — Keepouts</div>""",
        unsafe_allow_html=True,
    )

    # Ensure keepouts list exists
    if "keepouts" not in arr:
        arr["keepouts"] = []

    # ── Existing keepouts ──
    for i, ko in enumerate(arr["keepouts"]):
        ko_color = "#f1c40f"
        st.markdown(
            f"""<div style="font-size:11px;color:#666;margin-top:8px;">Keepout {i+1}</div>""",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns([3, 1])
        with c1:
            new_desc = st.text_input(
                "Description", value=ko.get("description", f"Keepout {i+1}"),
                key=f"ko_desc_{arr_id}_{i}", label_visibility="collapsed",
            )
            if new_desc != ko.get("description", f"Keepout {i+1}"):
                ko["description"] = new_desc
        with c2:
            if st.button("🗑️", key=f"ko_del_{arr_id}_{i}", use_container_width=True):
                arr["keepouts"].pop(i)
                _relayout_array(arr, load_components()[0])
                st.rerun()

        h1, h2 = st.columns([2, 1])
        with h1:
            new_height = st.number_input(
                "Height (m)", 0.0, 50.0, float(ko.get("height_m", 0.0)), step=0.1,
                key=f"ko_h_{arr_id}_{i}",
            )
            if new_height != ko.get("height_m", 0.0):
                ko["height_m"] = new_height
        with h2:
            new_active = st.checkbox(
                "Active", value=ko.get("active", True),
                key=f"ko_act_{arr_id}_{i}",
            )
            if new_active != ko.get("active", True):
                ko["active"] = new_active
                _relayout_array(arr, load_components()[0])
                st.rerun()
        st.divider()

    # ── Add new keepout ──
    if st.button("+ New Keepout", key=f"ko_new_{arr_id}", use_container_width=True):
        pass
    st.caption("Use the polygon or rectangle tool on the map to draw a keepout.")
