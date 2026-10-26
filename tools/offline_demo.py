"""Synthetic, network-denied demo of the original Suria calculation pipeline."""
from pathlib import Path
import argparse, copy, csv, hashlib, json, os, sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

def deny_network(event, args):
    if event in {"socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system"}:
        raise RuntimeError("Offline demo forbids network and child processes")

def synthetic_weather():
    import numpy as np
    import pandas as pd
    from pvlib.location import Location
    times = pd.date_range("2025-01-01", periods=8760, freq="h", tz="Asia/Kuala_Lumpur")
    loc = Location(3.14, 101.69, tz="Asia/Kuala_Lumpur", altitude=50)
    # Mathematical clear-sky fixture, NOT measured weather or PVGIS TMY.
    weather = loc.get_clearsky(times, model="ineichen")
    weather["temp_air"] = 28.0 + 3.0 * np.sin(2 * np.pi * (times.hour - 6) / 24)
    weather["wind_speed"] = 1.5
    return weather, 3.14, 101.69, 50

def sample_project():
    import pandas as pd
    mod = pd.read_csv(ROOT / "src/suria/components/modules.csv").fillna("").iloc[0].to_dict()
    inv = pd.read_csv(ROOT / "src/suria/components/inverters.csv").fillna("").iloc[0].to_dict()
    # Explicitly avoid CEC lookup fallback changes for this deterministic fixture.
    mod["cec_name"] = ""
    inv["cec_name"] = ""
    return {"name":"SYNTHETIC OFFLINE DEMO", "customer":"Example only", "designer":"Suria demo",
        "project_notes":"SYNTHETIC clear-sky weather, not PVGIS or a real site. No accuracy certification. Satellite map omitted. Monthly/hourly energy is before configured losses; annual energy is after losses. Historic accuracy footer is not verified.",
        "site":{"lat":3.14,"lon":101.69,"altitude":50,"tz":"Asia/Kuala_Lumpur"},
        "arrays":[{"name":"Array 1","coords":[],"tilt":10,"azimuth":180,"modules_per_string":10,"strings":1,"module":mod["name"],"inverter":inv["name"],"row_spacing_m":2.0}],
        "module_specs":{mod["name"]:mod},"inverter_specs":{inv["name"]:inv},"tariff_block":"E1"}

def execute(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    os.chdir(output)
    os.environ["MPLBACKEND"] = "Agg"
    from suria import simulate, storage
    from suria.electrical import validate_project_electrical
    from suria.financials import calculate_financials
    from suria.layout import estimate_panels_from_polygon
    from suria.reporter.render import render_report
    project = sample_project()
    fixture = synthetic_weather()
    fixture[0].to_csv(output / "synthetic-weather.csv", index_label="timestamp")
    with patch.object(simulate, "get_pvgis_weather", return_value=fixture):
        result = simulate.simulate_project(project)
    result["electrical"] = validate_project_electrical(project)
    result["system_cost_rm"] = 30000.0
    result["financials"] = calculate_financials(result["annual_ac_kwh"], 30000.0)
    assert result["annual_ac_kwh"] > 0
    assert len(result["hourly_ac"]) == 8760 and len(result["monthly_ac_kwh"]) == 12
    storage.DB_PATH = output / "demo-projects.db"
    identity = storage.save_project(project)
    assert storage.load_project(identity) == project
    assert storage.save_project(project) == identity and len(storage.list_projects()) == 1
    report = render_report(project, result, output / "synthetic-report.pdf")
    assert report.read_bytes().startswith(b"%PDF-") and report.stat().st_size > 10000
    coords = [[101.69,3.14],[101.6902,3.14],[101.6902,3.1402],[101.69,3.1402],[101.69,3.14]]
    count, centers, rectangles = estimate_panels_from_polygon(coords, 2.0, 1.0, 2.0, 0.5)
    assert count == len(centers) == len(rectangles) and count > 0
    (output / "project.json").write_text(json.dumps(project, indent=2), encoding="utf-8")
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    summary = {"fixture":"synthetic mathematical clear-sky, 8760 hours", "source_module":str(Path(simulate.__file__).resolve()), "annual_after_losses_kwh": result["annual_ac_kwh"], "monthly_before_losses_sum_kwh":sum(result["monthly_ac_kwh"]), "layout_panel_count":count, "sqlite_round_trip":True,"pdf_bytes":report.stat().st_size,"network_allowed":False}
    (output / "summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return result

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True, help="New output directory; existing directories are refused")
    args=parser.parse_args()
    sys.addaudithook(deny_network)
    execute(args.output)
