"""Step 3: Simulation results, loss breakdown, financials, PDF export."""
from pathlib import Path

import pandas as pd
import streamlit as st

from suria.financials import calculate_financials
from suria.reporter.render import render_report
from suria.storage import save_project


def render_step3_results():
    """Step 3: Simulation results, loss breakdown, financials, PDF export."""
    st.header("Results")
    st.caption("Archived unsupported output; illustrative assumptions only. Not a design or eligibility assessment.")

    if not st.session_state.get("result"):
        st.info("No simulation results yet. Go back to Map Design and run a simulation.")
        if st.button("← Back to Map Design"):
            st.session_state["ui_step"] = 2
            st.rerun()
        return

    r = st.session_state["result"]
    p = st.session_state["project"]

    # System overview
    st.subheader("System Overview")
    dc_kw = sum(
        a["modules_per_string"] * a["strings"] * p["module_specs"][a["module"]]["p_max"] / 1000
        for a in p["arrays"]
    )
    ac_kw = sum(p["inverter_specs"][a["inverter"]]["p_aco"] / 1000 for a in p["arrays"])
    ratio = dc_kw / ac_kw if ac_kw > 0 else 0

    # Unused historical interval arithmetic; unsupported and not displayed
    variance_pct = 3.8
    yield_low = r['annual_ac_kwh'] * (1 - variance_pct / 100)
    yield_high = r['annual_ac_kwh'] * (1 + variance_pct / 100)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("DC Capacity", f"{dc_kw:.2f} kWp")
    c2.metric("Annual Energy (post-loss)", f"{r['annual_ac_kwh']:,.0f} kWh")
    c3.metric("Specific Yield", f"{r['specific_yield']:,.0f} kWh/kWp")
    c4.metric("Capacity Factor", f"{r['capacity_factor']:.1f}%")
    st.caption(
        "No validated uncertainty interval. Annual energy includes additional losses; "
        "monthly, hourly and mean power outputs do not. These branches do not reconcile."
    )

    # Project assumptions
    with st.expander("Project Assumptions"):
        losses = p.get("losses", {})
        a1, a2, a3 = st.columns(3)
        a1.metric("Soiling", f"{losses.get('soiling', 2.0)}%")
        a1.metric("Mismatch", f"{losses.get('mismatch', 2.0)}%")
        a2.metric("DC Wiring", f"{losses.get('wiring', 1.5)}%")
        a2.metric("Availability", f"{losses.get('availability', 1.0)}%")
        a3.metric("LID", f"{losses.get('lid', 1.5)}%")
        a3.metric("AC System", f"{losses.get('ac_system', 0.5)}%")
        st.caption(f"Export rate: {st.session_state.get('solar_atap_export_rate', 0.25):.2f} RM/kWh")

    # Array details
    st.subheader("Array Details")
    arr_rows = []
    for i, a in enumerate(p["arrays"], 1):
        mod = p["module_specs"][a["module"]]
        dc = a["modules_per_string"] * a["strings"] * mod["p_max"] / 1000
        arr_rows.append({
            "Array": a["name"],
            "Module": a["module"],
            "Inverter": a["inverter"],
            "Tilt": f"{a['tilt']}°",
            "Azimuth": f"{a['azimuth']}°",
            "Strings": a["strings"],
            "Mod/Str": a["modules_per_string"],
            "Shading Loss": f"{a.get('shading_loss_pct', 2.0)}%",
            "Orient": "Portrait" if a.get("portrait") else "Landscape",
            "DC (kWp)": f"{dc:.2f}",
        })
    st.dataframe(pd.DataFrame(arr_rows), use_container_width=True, hide_index=True)

    # Monthly production
    st.subheader("Monthly Energy (before additional losses)")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    chart_data = pd.DataFrame({"Month": months, "kWh": r["monthly_ac_kwh"]})
    st.bar_chart(chart_data.set_index("Month"))

    # Daily average production profile
    if "daily_profile" in r:
        st.subheader("Mean AC Power (before additional losses)")
        hours = [f"{h:02d}:00" for h in range(24)]
        prof_df = pd.DataFrame({"Hour": hours, "AC Power (kW)": r["daily_profile"]})
        st.line_chart(prof_df.set_index("Hour"))
        peak_hour = max(range(24), key=lambda h: r["daily_profile"][h])
        st.caption(f"Peak average output at **{peak_hour:02d}:00** — **{r['daily_profile'][peak_hour]:.2f} kW**")

    # Loss breakdown
    st.subheader("Loss Breakdown")
    if "losses" in r:
        loss_df = pd.DataFrame({
            "Category": [k.replace("_", " ").title() for k in r["losses"].keys()],
            "Loss (%)": list(r["losses"].values()),
        }).sort_values("Loss (%)", ascending=False)
        st.bar_chart(loss_df.set_index("Category"))
        composite_factor = 1.0
        for v in r["losses"].values():
            composite_factor *= (1 - v / 100)
        composite_loss_pct = (1 - composite_factor) * 100
        st.caption(f"Diagnostic categories, not reconciled to annual output. Composite = {composite_loss_pct:.1f}%")
    else:
        st.info("Loss breakdown not available.")

    # Canonical loss waterfall
    if "loss_diagnostic" in r:
        with st.expander("View Loss Waterfall"):
            from suria.reporter.render import _waterfall_chart_bytes
            wf_buf = _waterfall_chart_bytes(r["loss_diagnostic"])
            st.image(wf_buf)
            diag_df = pd.DataFrame(r["loss_diagnostic"])
            diag_df = diag_df[["step", "pct", "energy_kwh", "source"]]
            diag_df.columns = ["Step", "Loss (%)", "Energy (kWh)", "Source"]
            st.dataframe(diag_df, use_container_width=True, hide_index=True)

    # Electrical validation
    if "electrical" in r:
        st.subheader("Electrical Validation")
        elec = r["electrical"]
        es = elec["summary"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("DC:AC Ratio", f"{es['overall_dc_ac_ratio']:.2f}")
        c2.metric("Errors", es["error_count"], delta_color="inverse")
        c3.metric("Warnings", es["warning_count"], delta_color="inverse")
        c4.metric("DC Power", f"{es['total_dc_w'] / 1000:.1f} kW")
        if es["error_count"] == 0 and es["warning_count"] == 0:
            st.success("No electrical issues detected.")
        else:
            for issue in elec["issues"][:5]:
                if issue["severity"] == "error":
                    st.error(issue["message"])
                elif issue["severity"] == "warning":
                    st.warning(issue["message"])
                else:
                    st.info(issue["message"])

        with st.expander("Per-Array Electrical Details"):
            for arr in elec.get("arrays", []):
                st.markdown(f"**{arr['name']}**  —  {arr['strings']} strings × {arr['modules_per_string']} modules = {arr['total_modules']} panels  |  DC:AC {arr['dc_ac_ratio']}")
                st.caption(f"V_oc max: {arr['string_v_max']:.1f} V  |  V_mp min: {arr['string_v_min']:.1f} V")
                if arr["issues"]:
                    for issue in arr["issues"][:3]:
                        icon = "🔴" if issue["severity"] == "error" else "🟡" if issue["severity"] == "warning" else "🔵"
                        st.write(f"{icon} {issue['message']}")
                else:
                    st.write("✅ No issues for this array.")
                st.divider()

    # Solar ATAP validation
    if "nem" in r:
        st.subheader("Solar ATAP Sizing Check")
        nem = r["nem"]
        nc1, nc2, nc3 = st.columns(3)
        nc1.metric("DC Capacity", f"{nem['dc_kw']:.1f} kWp")
        nc2.metric("ATAP Limit", f"{nem['applicable_limit_kw']:.1f} kWp")
        nc3.metric("Eligible", "Yes" if nem["nem_eligible"] else "No")
        for issue in nem["issues"]:
            if issue["severity"] == "error":
                st.error(issue["message"])
            elif issue["severity"] == "warning":
                st.warning(issue["message"])
            else:
                st.info(issue["message"])

    # Financials
    st.subheader("Illustrative Financial Scenario (historical rates)")
    cost_per_kw = st.number_input(
        "System cost (RM/kW)", value=float(st.session_state.get("system_cost_per_kw", 3500.0)), step=100.0
    )
    self_con = st.slider("Self-consumption %", 0, 100, int(st.session_state.get("self_consumption_pct", 70))) / 100
    tariff = st.selectbox("TNB Tariff Block", ["A", "B", "C", "D", "E1", "E2"], index=["A", "B", "C", "D", "E1", "E2"].index(st.session_state["tariff_block"]))

    total_cost = dc_kw * cost_per_kw
    export_rate = st.session_state.get("solar_atap_export_rate", 0.25)
    degradation = st.session_state.get("annual_degradation_pct", 0.5)
    fin = calculate_financials(r["annual_ac_kwh"], total_cost, self_con, tariff, export_rate_rm_per_kwh=export_rate, annual_degradation_pct=degradation)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("System Cost", f"RM {total_cost:,.0f}")
    c2.metric("Annual Benefit", f"RM {fin['total_annual_benefit_rm']:,.0f}")
    c3.metric("Payback", f"{fin['simple_payback_years']:.1f} years")
    c4.metric("Payback (with degradation)", f"{fin['payback_with_degradation_years']:.1f} years")

    fin_df = pd.DataFrame({
        "Item": ["Self-Consumption", "Export", "Savings", "Export Income", "Total Annual Benefit"],
        "kWh": [
            f"{fin['self_consumption_kwh']:,.0f}",
            f"{fin['export_kwh']:,.0f}",
            "-", "-", "-",
        ],
        "RM": [
            "-", "-",
            f"{fin['savings_rm']:,.0f}",
            f"{fin['export_income_rm']:,.0f}",
            f"{fin['total_annual_benefit_rm']:,.0f}",
        ],
    })
    st.dataframe(fin_df.set_index("Item"), use_container_width=True)

    # 25-year payback chart
    if fin.get("yearly_benefits"):
        from suria.reporter.render import _payback_chart_bytes
        try:
            payback_buf = _payback_chart_bytes(fin["yearly_benefits"], total_cost, width=7, height=3.5)
            st.image(payback_buf, use_container_width=True)
        except Exception:
            pass

        with st.expander("Year-by-Year Breakdown"):
            yearly_df = pd.DataFrame(fin["yearly_benefits"])
            yearly_df.columns = ["Year", "Annual Benefit (RM)", "Cumulative (RM)"]
            st.dataframe(yearly_df, use_container_width=True, hide_index=True)

    # Report export
    st.subheader("Report Export")
    pdf_col, csv_col = st.columns(2)
    with pdf_col:
        if st.button("Generate PDF", type="primary", use_container_width=True):
            with st.spinner("Generating PDF..."):
                safe_name = p['name'].replace(' ', '_').replace('/', '-')
                out = Path(f"{safe_name}_report.pdf")
                render_report(p, r, out)
            st.success(f"PDF saved: {out.resolve()}")
            with open(out, "rb") as f:
                st.download_button(
                    "Download PDF", f, file_name=f"{safe_name}_report.pdf", mime="application/pdf"
                )
    with csv_col:
        if st.button("Export Hourly CSV (pre-loss W)", type="secondary", use_container_width=True):
            hourly = r.get("hourly_ac", [])
            if hourly:
                df = pd.DataFrame(hourly)
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download CSV", csv, file_name=f"{p['name'].replace(' ', '_')}_hourly.csv", mime="text/csv"
                )
            else:
                st.warning("No hourly data available. Run simulation first.")

    # Save project
    if st.button("Save Project", type="secondary"):
        existing_id = p.get("saved_project_id")
        pid = save_project(p, project_id=existing_id)
        st.session_state["project"]["saved_project_id"] = pid
        from datetime import datetime
        st.session_state["last_saved"] = datetime.now().strftime("%H:%M:%S")
        st.success(f"Project saved (ID: {pid})")

    # Navigation
    st.divider()
    nav1, nav2 = st.columns(2)
    with nav1:
        if st.button("← Back to Map Design", use_container_width=True):
            st.session_state["ui_step"] = 2
            st.rerun()
    with nav2:
        if st.button("+ New Project", use_container_width=True):
            # Reset to defaults
            st.session_state["project_name"] = "Site A"
            st.session_state["customer"] = ""
            st.session_state["designer"] = ""
            st.session_state["project_notes"] = ""
            st.session_state["site_lat"] = 3.14
            st.session_state["site_lon"] = 101.69
            st.session_state["site_altitude"] = 50
            st.session_state["arrays"] = []
            st.session_state["next_array_id"] = 1
            st.session_state["result"] = None
            st.session_state["project"] = None
            st.session_state["ui_step"] = 1
            st.rerun()
