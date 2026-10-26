"""PDF report renderer using fpdf2."""
import math
from pathlib import Path
from io import BytesIO
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from staticmap import StaticMap, Polygon as StaticPolygon
import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from suria.domain.simulation_input import SimulationInput


def _lon_to_x(lon: float, zoom: int) -> float:
    return (lon + 180.0) / 360.0 * (2 ** zoom)


def _lat_to_y(lat: float, zoom: int) -> float:
    return (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * (2 ** zoom)


def _fit_zoom(lats, lons, width, height, max_zoom=19, pad=0.8):
    """Return the highest zoom level that fits bounds inside the image."""
    for z in range(22, 0, -1):
        dx = (_lon_to_x(max(lons), z) - _lon_to_x(min(lons), z)) * 256
        dy = (_lat_to_y(min(lats), z) - _lat_to_y(max(lats), z)) * 256
        if dx <= width * pad and dy <= height * pad:
            return min(z, max_zoom)
    return 1


def _monthly_chart_bytes(monthly_kwh: list, width: int = 6, height: int = 3.5, dpi: int = 150):
    """Return PNG bytes for a monthly production bar chart."""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    bars = ax.bar(months, monthly_kwh, color="#3498db", edgecolor="#2980b9", linewidth=0.5)
    ax.set_ylabel("kWh", fontsize=9)
    ax.set_title("Monthly Energy (before additional losses)", fontsize=11, fontweight="bold", color="#1a5276")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    # Add value labels on top of bars
    for bar in bars:
        height_val = bar.get_height()
        ax.annotate(
            f"{height_val:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, height_val),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom", fontsize=7, rotation=90,
        )
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _loss_chart_bytes(losses: dict, width: int = 6, height: int = 2.5, dpi: int = 150):
    """Return PNG bytes for a horizontal loss breakdown bar chart."""
    items = sorted(losses.items(), key=lambda x: x[1], reverse=True)
    labels = [k.replace("_", " ").title() for k, _ in items]
    values = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    colors = ["#e74c3c" if v > 5 else "#f39c12" if v > 2 else "#27ae60" for v in values]
    bars = ax.barh(labels, values, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Loss (%)", fontsize=8)
    ax.set_title("Loss Breakdown", fontsize=10, fontweight="bold", color="#1a5276")
    ax.invert_yaxis()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=7)
    for bar in bars:
        width_val = bar.get_width()
        ax.annotate(
            f"{width_val:.1f}%",
            xy=(width_val, bar.get_y() + bar.get_height() / 2),
            xytext=(3, 0),
            textcoords="offset points",
            ha="left", va="center", fontsize=7,
        )
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _waterfall_chart_bytes(diagnostic: list, width: int = 7, height: int = 3.5, dpi: int = 150):
    """Return PNG bytes for a canonical loss waterfall chart."""
    steps = [d["step"] for d in diagnostic]
    energies = [d["energy_kwh"] for d in diagnostic]
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    colors = ["#3498db" if i == 0 else "#2ecc71" if i == len(steps) - 1 else "#e74c3c" if diagnostic[i]["pct"] > 0 else "#95a5a6" for i in range(len(steps))]
    bars = ax.bar(steps, energies, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_ylabel("Energy (kWh)", fontsize=9)
    ax.set_title("Loss Waterfall", fontsize=11, fontweight="bold", color="#1a5276")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=7)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha="right")
    for bar in bars:
        height_val = bar.get_height()
        ax.annotate(
            f"{height_val:,.0f}",
            xy=(bar.get_x() + bar.get_width() / 2, height_val),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center", va="bottom", fontsize=6,
        )
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _schematic_chart_bytes(project: dict, width: int = 8, height: int = 3.5, dpi: int = 150):
    """Return PNG bytes for a simple single-line diagram."""
    arrays = project.get("arrays", [])
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("System Single-Line Diagram", fontsize=11, fontweight="bold", color="#1a5276")

    def box(x, y, w, h, label, color="#3498db"):
        rect = plt.Rectangle((x, y), w, h, facecolor=color, edgecolor="black", linewidth=1.5, alpha=0.85)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h / 2, label, ha="center", va="center", fontsize=7, color="white", fontweight="bold", wrap=True)

    n = len(arrays)
    if n == 0:
        ax.text(5, 5, "No arrays", ha="center", va="center", fontsize=10)
        fig.tight_layout()
        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return buf

    # Array boxes on the left
    arr_y_start = 7.0 if n <= 3 else 8.5
    arr_spacing = 2.5 if n <= 3 else 1.8
    for i, arr in enumerate(arrays):
        dc = arr["modules_per_string"] * arr["strings"] * project["module_specs"][arr["module"]]["p_max"] / 1000
        y = arr_y_start - i * arr_spacing
        box(0.5, y, 2.0, 1.2, f"{arr['name']}\n{dc:.1f} kWp", color="#3498db")
        # DC line to inverter
        ax.plot([2.5, 4.0], [y + 0.6, 5.0], color="#e74c3c", linewidth=2, linestyle="--")

    # Combiner / Inverter
    inv_names = list(dict.fromkeys(arr["inverter"] for arr in arrays))
    inv_label = inv_names[0] if len(inv_names) == 1 else "Inverters"
    box(4.0, 4.0, 2.0, 2.0, f"{inv_label}\nDC→AC", color="#2ecc71")

    # AC line to breaker
    ax.plot([6.0, 7.5], [5.0, 5.0], color="#f39c12", linewidth=2.5)

    # AC Breaker
    box(7.5, 4.3, 1.5, 1.4, "AC\nBreaker", color="#9b59b6")

    # Grid
    ax.plot([9.0, 9.8], [5.0, 5.0], color="#f39c12", linewidth=2.5)
    box(9.8, 4.3, 1.5, 1.4, "Grid /\nNEM Meter", color="#7f8c8d")

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _daily_chart_bytes(daily_profile: list, width: int = 6, height: int = 3.0, dpi: int = 150):
    """Return PNG bytes for a 24-hour average daily production profile chart."""
    hours = list(range(24))
    fig, ax = plt.subplots(figsize=(width, height), dpi=dpi)
    ax.plot(hours, daily_profile, color="#3498db", linewidth=2, marker="o", markersize=3)
    ax.fill_between(hours, daily_profile, alpha=0.3, color="#3498db")
    ax.set_xlabel("Hour", fontsize=9)
    ax.set_ylabel("kW (pre-loss)", fontsize=9)
    ax.set_title("Mean AC Power (before additional losses)", fontsize=11, fontweight="bold", color="#1a5276")
    ax.set_xticks(hours[::2])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="both", labelsize=8)
    ax.set_xlim(0, 23)
    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _payback_chart_bytes(yearly_benefits: list, system_cost_rm: float, width: int = 7, height: int = 3.5, dpi: int = 150):
    """Return PNG bytes for a 25-year cumulative benefit vs system cost chart."""
    years = [y["year"] for y in yearly_benefits]
    cumulative = [y["cumulative"] for y in yearly_benefits]
    annual = [y["benefit"] for y in yearly_benefits]

    fig, ax1 = plt.subplots(figsize=(width, height), dpi=dpi)

    # Cumulative benefit line
    ax1.plot(years, cumulative, color="#27ae60", linewidth=2.5, marker="o", markersize=4, label="Cumulative Benefit")
    ax1.fill_between(years, cumulative, alpha=0.15, color="#27ae60")

    # System cost horizontal line
    ax1.axhline(y=system_cost_rm, color="#e74c3c", linewidth=2, linestyle="--", label=f"System Cost RM {system_cost_rm:,.0f}")

    # Payback annotation
    for i, cum in enumerate(cumulative):
        if cum >= system_cost_rm:
            ax1.annotate(
                f"Payback\nYear {years[i]}",
                xy=(years[i], cum),
                xytext=(years[i] + 3, system_cost_rm * 0.9),
                fontsize=8,
                color="#1a5276",
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#1a5276", lw=1.2),
            )
            break

    ax1.set_xlabel("Year", fontsize=9)
    ax1.set_ylabel("Cumulative Benefit (RM)", fontsize=9, color="#27ae60")
    ax1.tick_params(axis="y", labelcolor="#27ae60", labelsize=8)
    ax1.set_xticks(years[::2])
    ax1.set_xlim(1, 25)
    ax1.spines["top"].set_visible(False)

    # Annual benefit bars on secondary axis
    ax2 = ax1.twinx()
    ax2.bar(years, annual, alpha=0.25, color="#3498db", width=0.6, label="Annual Benefit")
    ax2.set_ylabel("Annual Benefit (RM)", fontsize=9, color="#3498db")
    ax2.tick_params(axis="y", labelcolor="#3498db", labelsize=8)
    ax2.spines["top"].set_visible(False)

    ax1.set_title("25-Year Financial Projection", fontsize=11, fontweight="bold", color="#1a5276")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=7)

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# Same palette as the Streamlit UI
_ARRAY_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12", "#9b59b6", "#1abc9c", "#e67e22", "#34495e"]


def render_map_image(project: dict, width: int = 700, height: int = 400):
    """Render a static satellite map with array polygon overlays."""
    arrays = project.get("arrays", [])
    if not arrays or not arrays[0].get("coords"):
        return None

    m = StaticMap(
        width, height,
        url_template="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    )

    all_coords = []
    for i, arr in enumerate(arrays):
        coords = arr.get("coords", [])
        if not coords:
            continue
        all_coords.extend(coords)
        # Stored coords are GeoJSON [lon, lat]; staticmap expects (lon, lat) tuples
        poly_coords = [(c[0], c[1]) for c in coords]
        color = _ARRAY_COLORS[i % len(_ARRAY_COLORS)]
        poly = StaticPolygon(
            poly_coords,
            fill_color=f"{color}4d",  # 30% opacity
            outline_color=color,
        )
        m.add_polygon(poly)

    # Compute manual zoom — staticmap auto-zoom caps at 17, rooftop solar needs 19
    lats = [c[1] for c in all_coords]
    lons = [c[0] for c in all_coords]
    zoom = _fit_zoom(lats, lons, width, height)
    center = [(min(lons) + max(lons)) / 2, (min(lats) + max(lats)) / 2]

    image = m.render(zoom=zoom, center=center)
    return image


class ReportPDF(FPDF):
    def header(self):
        # Blue header bar
        self.set_fill_color(26, 82, 118)
        self.rect(0, 0, 210, 18, style="F")
        self.set_y(5)
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "SURIA  -  Solar PV Pre-Feasibility Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def render_report(project: dict, result: dict, output_path: Path):
    """Render a professional PDF report."""
    SimulationInput.model_validate(project)
    dc_kw = sum(
        arr["modules_per_string"] * arr["strings"] * project["module_specs"][arr["module"]]["p_max"] / 1000
        for arr in project["arrays"]
    )
    ac_kw = sum(
        project["inverter_specs"][arr["inverter"]]["p_aco"] / 1000
        for arr in project["arrays"]
    )

    pdf = ReportPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Project title block
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 10, project["name"], new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Customer: {project['customer']}  |  Designer: {project['designer']}  |  Date: {datetime.date.today().isoformat()}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    notes = project.get("project_notes", "")
    if notes:
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 5, f"Notes: {notes}")
        pdf.set_text_color(0, 0, 0)
    # Horizontal rule
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    # Site
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "Site Location", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    s = project["site"]
    pdf.cell(0, 6, f"Latitude: {s['lat']:.4f}  |  Longitude: {s['lon']:.4f}  |  Altitude: {s['altitude']} m", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(2)

    # Map image
    map_img = render_map_image(project)
    if map_img:
        buf = BytesIO()
        map_img.save(buf, format="PNG")
        buf.seek(0)
        pdf.image(buf, w=180)
        pdf.ln(2)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(128, 128, 128)
        pdf.cell(0, 4, "Satellite imagery: Esri World Imagery", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    # System overview
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "System Overview", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)

    # Row 1: capacity metrics
    r1_headers = ["DC Capacity", "AC Capacity", "DC:AC Ratio", "Annual (post-loss)"]
    r1_values = [f"{dc_kw:.2f} kWp", f"{ac_kw:.2f} kW", f"{dc_kw/ac_kw:.2f}",
                 f"{result['annual_ac_kwh']:,.0f} kWh"]
    col_w = 45
    for h, v in zip(r1_headers, r1_values):
        pdf.set_fill_color(238, 238, 255)
        pdf.cell(col_w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    for v in r1_values:
        pdf.cell(col_w, 7, v, border=1, align="C")
    pdf.ln()
    # Row 2: yield metrics
    r2_headers = ["Specific Yield", "Capacity Factor", "Performance Ratio"]
    r2_values = [f"{result['specific_yield']:,.0f} kWh/kWp",
                   f"{result.get('capacity_factor', 0):.1f}%",
                   f"{result.get('performance_ratio', 0):.1f}%"]
    for h, v in zip(r2_headers, r2_values):
        pdf.set_fill_color(238, 238, 255)
        pdf.cell(col_w, 7, h, border=1, fill=True, align="C")
    pdf.cell(col_w, 7, "", border=0)
    pdf.ln()
    for v in r2_values:
        pdf.cell(col_w, 7, v, border=1, align="C")
    pdf.cell(col_w, 7, "", border=0)
    pdf.ln(8)

    # System Schematic
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "System Schematic", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Courier", "", 7)
    pdf.set_text_color(0, 0, 0)

    arrays = project["arrays"]
    arr_parts = []
    for arr in arrays:
        dc = arr["modules_per_string"] * arr["strings"] * project["module_specs"][arr["module"]]["p_max"] / 1000
        arr_parts.append(f"[{arr['name']}: {dc:.1f} kWp]")

    if len(arr_parts) == 1:
        schematic = (
            f"{arr_parts[0]}--DC-->[Inverter: {arrays[0]['inverter']}]--AC-->"
            f"[AC Breaker]--AC-->[Grid / NEM Meter]"
        )
    else:
        max_len = max(len(p) for p in arr_parts)
        mid = len(arr_parts) // 2
        lines = []
        for i, part in enumerate(arr_parts):
            pad = " " * (max_len - len(part))
            connector = "--+"
            if i == mid:
                connector += (
                    "--[Combiner Box]--DC-->[Inverter]--AC-->"
                    "[AC Breaker]--AC-->[Grid / NEM Meter]"
                )
            lines.append(f"{part}{pad}{connector}")
        schematic = "\n".join(lines)

    pdf.multi_cell(0, 5, schematic)
    pdf.ln(2)
    try:
        schematic_buf = _schematic_chart_bytes(project, width=8, height=3.5)
        pdf.image(schematic_buf, w=180)
    except Exception:
        pass  # Fallback: text schematic already shown
    pdf.ln(6)

    # Arrays
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "Arrays", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(238, 238, 255)
    arr_headers = ["#", "Name", "Module", "Inverter", "Tilt", "Azimuth", "Strings", "Mod/String"]
    col_ws = [8, 25, 28, 28, 18, 22, 18, 22]
    for h, w in zip(arr_headers, col_ws):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for i, arr in enumerate(project["arrays"], 1):
        row = [str(i), arr["name"], arr["module"], arr["inverter"],
               f"{arr['tilt']} deg", f"{arr['azimuth']} deg", str(arr["strings"]), str(arr["modules_per_string"])]
        for v, w in zip(row, col_ws):
            pdf.cell(w, 7, v, border=1, align="C")
        pdf.ln()
    pdf.ln(2)

    # Keepout summary
    has_keepouts = any(arr.get("keepouts") for arr in project["arrays"])
    if has_keepouts:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(241, 196, 15)
        pdf.cell(0, 6, "Keepouts (Obstructions)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(0, 0, 0)
        for arr in project["arrays"]:
            for ko in arr.get("keepouts", []):
                if not ko.get("active", True):
                    continue
                desc = ko.get("description", "Keepout")
                h = ko.get("height_m", 0.0)
                status = "Active" if ko.get("active", True) else "Inactive"
                pdf.cell(0, 5, f"  {arr['name']}: {desc}  |  Height: {h:.1f} m  |  {status}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    pdf.ln(2)

    # Bill of Materials
    total_modules = sum(arr["modules_per_string"] * arr["strings"] for arr in project["arrays"])
    total_strings = sum(arr["strings"] for arr in project["arrays"])
    total_inverters = len(project["arrays"])
    dc_cable_m = total_strings * 30
    ac_cable_m = ac_kw  # 10m per 10kW AC
    rail_m = total_modules * 2.5
    clamps = total_modules * 4
    dc_spds = total_inverters
    ac_spds = total_inverters

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "Bill of Materials", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(238, 238, 255)
    bom_headers = ["Item", "Description", "Unit", "Qty"]
    bom_ws = [50, 80, 25, 25]
    for h, w in zip(bom_headers, bom_ws):
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)

    inverter_models = list(dict.fromkeys(arr["inverter"] for arr in project["arrays"]))
    inv_desc = inverter_models[0] if len(inverter_models) == 1 else "Mixed"

    bom_rows = [
        ["PV Modules", project["arrays"][0]["module"] if project["arrays"] else "", "pcs", str(total_modules)],
        ["Inverters", inv_desc, "pcs", str(total_inverters)],
        ["DC Cabling", "PV1-F 4mm2 or equivalent", "m", f"{dc_cable_m:.0f}"],
        ["AC Cabling", "5-core AC cable", "m", f"{ac_cable_m:.0f}"],
        ["Mounting Rails", "Aluminium rail, landscape", "m", f"{rail_m:.0f}"],
        ["Mid / End Clamps", "Stainless steel", "pcs", f"{clamps:.0f}"],
        ["DC SPD", "Type 1+2", "pcs", str(dc_spds)],
        ["AC SPD", "Type 2", "pcs", str(ac_spds)],
    ]
    for row in bom_rows:
        for idx, (v, w) in enumerate(zip(row, bom_ws)):
            align = "L" if idx < 2 else "C"
            pdf.cell(w, 7, v, border=1, align=align)
        pdf.ln()
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5, "Note: BOM is indicative only. Final quantities depend on site survey and detailed design.")
    pdf.ln(6)

    # Monthly production chart
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "Monthly Energy (before additional losses)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    monthly_buf = _monthly_chart_bytes(result["monthly_ac_kwh"], height=3.5)
    pdf.image(monthly_buf, w=180)
    pdf.ln(4)

    # Daily production profile chart
    if "daily_profile" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Mean AC Power (before additional losses)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        daily_buf = _daily_chart_bytes(result["daily_profile"], height=3.0)
        pdf.image(daily_buf, w=180)
        pdf.ln(4)

    # Loss Breakdown chart
    if "losses" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Loss Breakdown", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        loss_buf = _loss_chart_bytes(result["losses"])
        pdf.image(loss_buf, w=120)
        pdf.ln(4)

    # Waterfall chart
    if "loss_diagnostic" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Loss Waterfall", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        wf_buf = _waterfall_chart_bytes(result["loss_diagnostic"])
        pdf.image(wf_buf, w=180)
        pdf.ln(4)

    # Canonical HelioScope-format loss tree table
    if "loss_tree" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Experimental Loss Diagnostics (not reconciled)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(238, 238, 255)
        tree_headers = ["Step", "Loss (%)", "Energy (kWh)"]
        tree_ws = [60, 35, 35]
        for h, w in zip(tree_headers, tree_ws):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        for entry in result.get("loss_diagnostic", []):
            row = [
                entry["step"],
                f"{entry['pct']:.2f}%" if entry["pct"] != 0.0 else "—",
                f"{entry['energy_kwh']:,.1f}",
            ]
            for v, w in zip(row, tree_ws):
                align = "L" if v == entry["step"] else "R"
                pdf.cell(w, 7, v, border=1, align=align)
            pdf.ln()
        pdf.ln(4)

    # Project assumptions
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(26, 82, 118)
    pdf.cell(0, 8, "Project Assumptions", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(0, 0, 0)
    losses = project.get("losses", {})
    pdf.cell(0, 6, f"Soiling {losses.get('soiling', 2.0)}%  |  Mismatch {losses.get('mismatch', 2.0)}%  |  Wiring {losses.get('wiring', 1.5)}%  |  Availability {losses.get('availability', 1.0)}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"LID {losses.get('lid', 1.5)}%  |  AC System {losses.get('ac_system', 0.5)}%  |  Export Rate RM {project.get('solar_atap_export_rate', 0.25):.2f}/kWh", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Self-consumption: {project.get('self_consumption_pct', 0.70) * 100:.0f}%  |  Annual Degradation: {project.get('annual_degradation_pct', 0.5)}%", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # Solar ATAP validation summary
    if "nem" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Solar ATAP Sizing Validation", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        nem = result["nem"]
        pdf.cell(0, 6, f"Consumer Type: {nem['consumer_type'].replace('_', ' ').title()}  |  DC:AC Ratio: {nem['dc_ac_ratio']:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"DC Capacity: {nem['dc_kw']:.1f} kWp  |  ATAP Limit: {nem['applicable_limit_kw']:.1f} kWp", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if nem["nem_eligible"]:
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 6, "System is eligible for Solar ATAP self-consumption.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 6, "System does NOT meet Solar ATAP sizing rules.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
        for issue in nem["issues"]:
            if issue["severity"] == "error":
                pdf.set_text_color(200, 0, 0)
                sev = "ERROR"
            elif issue["severity"] == "warning":
                pdf.set_text_color(255, 140, 0)
                sev = "WARN"
            else:
                pdf.set_text_color(0, 0, 0)
                sev = "INFO"
            pdf.cell(0, 5, f"  [{sev}] {issue['message']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(6)

    # Financials
    if "financials" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Financials (Solar ATAP)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        fin = result["financials"]
        system_cost = result.get("system_cost_rm", 0)
        pdf.cell(0, 6, f"System Cost: RM {system_cost:,.0f}  |  Payback: {fin['simple_payback_years']:.1f} years  |  Payback (with degradation): {fin.get('payback_with_degradation_years', 'N/A'):.1f} years", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Tariff: RM {fin['tariff_rm_per_kwh']:.3f}/kWh  |  Export Rate: RM {fin['export_rate_rm_per_kwh']:.2f}/kWh  |  25-yr Total Benefit: RM {fin.get('total_25yr_benefit_rm', 0):,.0f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

        # 25-year payback chart
        if fin.get("yearly_benefits"):
            try:
                payback_buf = _payback_chart_bytes(fin["yearly_benefits"], system_cost, width=7, height=3.5)
                pdf.image(payback_buf, w=180)
                pdf.ln(2)
            except Exception:
                pass  # Graceful fallback if chart generation fails

        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(238, 238, 255)
        fin_headers = ["Item", "kWh", "RM"]
        fin_ws = [80, 35, 35]
        for h, w in zip(fin_headers, fin_ws):
            pdf.cell(w, 7, h, border=1, fill=True, align="C")
        pdf.ln()
        pdf.set_font("Helvetica", "", 9)
        fin_rows = [
            ["Self-Consumption", f"{fin['self_consumption_kwh']:,.0f}", "-"],
            ["Export", f"{fin['export_kwh']:,.0f}", "-"],
            ["Savings (self-consumed)", "-", f"RM {fin['savings_rm']:,.0f}"],
            ["Export Income", "-", f"RM {fin['export_income_rm']:,.0f}"],
            ["Total Annual Benefit", "-", f"RM {fin['total_annual_benefit_rm']:,.0f}"],
        ]
        for row in fin_rows:
            for idx, (v, w) in enumerate(zip(row, fin_ws)):
                align = "L" if idx == 0 else "R"
                bold = idx == 0 and "Total" in v
                if bold:
                    pdf.set_font("Helvetica", "B", 9)
                pdf.cell(w, 7, v, border=1, align=align)
                if bold:
                    pdf.set_font("Helvetica", "", 9)
            pdf.ln()
        pdf.ln(6)

    # Electrical validation summary
    if "electrical" in result:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(26, 82, 118)
        pdf.cell(0, 8, "Electrical Validation", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(0, 0, 0)
        elec = result["electrical"]
        pdf.cell(0, 6, f"Overall DC:AC Ratio: {elec['summary']['overall_dc_ac_ratio']:.2f}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 6, f"Total DC Power: {elec['summary']['total_dc_w']/1000:.1f} kW  |  Total AC Power: {elec['summary']['total_ac_w']/1000:.1f} kW", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if elec["issues"]:
            pdf.set_text_color(200, 0, 0)
            pdf.cell(0, 6, f"Issues found: {elec['summary']['issue_count']} ({elec['summary']['error_count']} errors, {elec['summary']['warning_count']} warnings)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
            for issue in elec["issues"][:5]:  # show first 5
                sev = "ERROR" if issue["severity"] == "error" else "WARN"
                pdf.cell(0, 5, f"  [{sev}] {issue['message']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            pdf.set_text_color(0, 128, 0)
            pdf.cell(0, 6, "No electrical issues detected.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

        # Per-array electrical details table
        if elec.get("arrays"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(26, 82, 118)
            pdf.cell(0, 6, "Per-Array Details", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_fill_color(238, 238, 255)
            elec_headers = ["Array", "V_oc max (V)", "V_mp min (V)", "DC:AC", "Modules", "Issues"]
            elec_ws = [40, 30, 30, 20, 25, 35]
            for h, w in zip(elec_headers, elec_ws):
                pdf.cell(w, 6, h, border=1, fill=True, align="C")
            pdf.ln()
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(0, 0, 0)
            for arr_detail in elec["arrays"]:
                issue_count = len(arr_detail.get("issues", []))
                issue_text = "OK" if issue_count == 0 else f"{issue_count} issue(s)"
                if issue_count > 0:
                    errs = sum(1 for i in arr_detail["issues"] if i["severity"] == "error")
                    if errs > 0:
                        issue_text = f"{issue_count} ({errs} err)"
                row = [
                    arr_detail["name"],
                    f"{arr_detail['string_v_max']:.0f}",
                    f"{arr_detail['string_v_min']:.0f}",
                    f"{arr_detail['dc_ac_ratio']:.2f}",
                    str(arr_detail["total_modules"]),
                    issue_text,
                ]
                for v, w in zip(row, elec_ws):
                    align = "L" if v == arr_detail["name"] else "C"
                    pdf.cell(w, 6, v, border=1, align=align)
                pdf.ln()
            pdf.ln(4)

        pdf.ln(2)

    # Footer disclaimer
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(128, 128, 128)
    pdf.multi_cell(0, 5,
        "Archived experimental output. Not for construction, eligibility or investment decisions.\n"
        "Weather provenance depends on the caller; no accuracy interval is established. Financial values are illustrative historical assumptions.")

    pdf.output(str(output_path))
    return output_path
