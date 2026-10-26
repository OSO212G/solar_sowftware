"""Component picker panel for module / inverter selection."""
import streamlit as st

from suria.ui.layout_utils import _relayout_array


def render_component_picker(mode, arr_id, modules, inverters):
    """Show a searchable library table for module or inverter selection."""
    st.markdown(f"""<span style="font-size:14px;font-weight:600;color:#333;">Select {mode.title()}</span>""", unsafe_allow_html=True)
    if st.button("← Cancel", key=f"pick_cancel_{mode}", use_container_width=True):
        st.session_state["picker_mode"] = None
        st.session_state["picker_array_id"] = None
        st.rerun()

    arr = next((a for a in st.session_state["arrays"] if a["id"] == arr_id), None)
    if not arr:
        st.error("Array not found.")
        return

    if mode == "module":
        search = st.text_input("Search modules", "", key="pick_mod_search")
        df = modules.copy()
        if search.strip():
            df = df[df["name"].str.contains(search, case=False, na=False)]
        st.caption(f"Showing {len(df)} modules")
        display = df[["name", "p_max", "voc", "vmp", "isc", "imp"]].rename(columns={
            "name": "Name", "p_max": "Power (W)", "voc": "Voc", "vmp": "Vmp", "isc": "Isc", "imp": "Imp"
        })
        event = st.dataframe(display, use_container_width=True, selection_mode="single-row", on_select="rerun", key="pick_mod_table")
        if event.selection and event.selection.rows:
            idx = event.selection.rows[0]
            selected_name = df.iloc[idx]["name"]
            if selected_name != arr["module"]:
                arr["module"] = selected_name
                _relayout_array(arr, modules)
            st.session_state["picker_mode"] = None
            st.session_state["picker_array_id"] = None
            st.rerun()
    else:
        search = st.text_input("Search inverters", "", key="pick_inv_search")
        df = inverters.copy()
        if search.strip():
            df = df[df["name"].str.contains(search, case=False, na=False)]
        st.caption(f"Showing {len(df)} inverters")
        display = df[["name", "p_aco", "vdcmax", "vdcmin"]].rename(columns={
            "name": "Name", "p_aco": "AC Power (W)", "vdcmax": "Vdcmax", "vdcmin": "Vdcmin"
        })
        event = st.dataframe(display, use_container_width=True, selection_mode="single-row", on_select="rerun", key="pick_inv_table")
        if event.selection and event.selection.rows:
            idx = event.selection.rows[0]
            selected_name = df.iloc[idx]["name"]
            arr["inverter"] = selected_name
            st.session_state["picker_mode"] = None
            st.session_state["picker_array_id"] = None
            st.rerun()
