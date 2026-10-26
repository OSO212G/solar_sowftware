"""Cached component loader for Streamlit sessions."""
from pathlib import Path

import pandas as pd
import streamlit as st


@st.cache_data
def load_components():
    """Load module and inverter DataFrames from CSV files."""
    base = Path(__file__).resolve().parent.parent / "components"
    modules = pd.read_csv(base / "modules.csv")
    inverters = pd.read_csv(base / "inverters.csv")
    return modules, inverters
