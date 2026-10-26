"""Step indicator widget for the 3-step wizard."""
import streamlit as st


def step_indicator(current: int):
    """Render a simple step indicator at the top."""
    c1, c2, c3 = st.columns(3)
    steps = ["1. Project Settings", "2. Map Design", "3. Results"]
    cols = [c1, c2, c3]
    for i, (col, label) in enumerate(zip(cols, steps), 1):
        if i == current:
            col.markdown(f"**→ {label}**")
        elif i < current:
            col.markdown(f":white_check_mark: ~~{label}~~")
        else:
            col.markdown(f"{label}")
