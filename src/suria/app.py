"""Suria Streamlit app — Phase 2: HelioScope-style 3-step wizard."""
import sys
from pathlib import Path

# Ensure src/ is on Python path so `import suria` works when run directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from suria.ui.style import HELIOSCOPE_CSS
from suria.ui.state import init_session
from suria.ui.widgets.step_indicator import step_indicator
from suria.ui.pages.step1_settings import render_step1_project_settings
from suria.ui.pages.step2_map import render_step2_map_design
from suria.ui.pages.step3_results import render_step3_results

st.set_page_config(page_title="Suria — Solar PV Pre-Feasibility", layout="wide")


def main():
    init_session()
    step = st.session_state.get("ui_step", 1)

    # Inject custom CSS
    st.markdown(HELIOSCOPE_CSS, unsafe_allow_html=True)

    if step == 1:
        # Step 1 keeps the header and step indicator
        st.title("Suria")
        st.caption("Solar PV Pre-Feasibility Tool for Malaysia & Southeast Asia")
        step_indicator(step)
        st.divider()
        render_step1_project_settings()
    elif step == 2:
        # Step 2 is the HelioScope-style full-screen canvas
        render_step2_map_design()
    elif step == 3:
        st.title("Suria")
        st.caption("Solar PV Pre-Feasibility Tool for Malaysia & Southeast Asia")
        step_indicator(step)
        st.divider()
        render_step3_results()


if __name__ == "__main__":
    main()
