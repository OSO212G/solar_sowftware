"""Layout helpers for the Streamlit UI."""
from suria.domain.frame import make_frame
from suria.layout import estimate_panels_from_polygon, calculate_row_spacing


def _relayout_array(arr, modules, frame=None):
    """Re-calculate panel rectangles for an array based on current settings.

    Preserves user-set modules_per_string and strings — only updates the visual
    panel rectangles on the map. String config is controlled manually in the panel.
    """
    if not arr.get("coords"):
        return
    mod_match = modules[modules["name"] == arr["module"]]
    if mod_match.empty:
        return
    mod_row = mod_match.iloc[0]
    panel_l = mod_row["length"]
    panel_w = mod_row["width"]
    portrait = arr.get("portrait", False)
    panel_height = panel_l if portrait else panel_w
    # Respect user-set row spacing; fall back to auto-calculation
    spacing = arr.get("row_spacing_m", calculate_row_spacing(arr["tilt"], panel_height))
    keepouts = arr.get("keepouts")
    if frame is None and arr.get("coords"):
        first = arr["coords"][0]
        frame = make_frame(first[1], first[0])
    count, centers, rectangles = estimate_panels_from_polygon(
        arr["coords"], panel_l, panel_w, spacing,
        setback_m=arr.get("setback_m", 0.5), portrait=portrait, azimuth=arr["azimuth"],
        keepouts=keepouts, frame=frame,
    )
    arr["panel_rectangles"] = rectangles
    arr["panel_count"] = count
    # Auto-adjust string config if it exceeds the actual panel count
    total_strung = arr.get("modules_per_string", 1) * arr.get("strings", 1)
    if count > 0 and total_strung > count:
        arr["strings"] = max(1, count // arr["modules_per_string"])
