"""Additional verification; original source and original assertions are unchanged."""
from pathlib import Path
import copy, sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from offline_demo import synthetic_weather, sample_project

def test_real_pvlib_pipeline_with_synthetic_weather(monkeypatch):
    from suria import simulate
    assert Path(simulate.__file__).resolve().is_relative_to(ROOT/"src")
    monkeypatch.setattr(simulate,"get_pvgis_weather",lambda lat,lon:synthetic_weather())
    result=simulate.simulate_project(sample_project())
    assert result["annual_ac_kwh"]>0
    assert len(result["monthly_ac_kwh"])==12 and len(result["hourly_ac"])==8760
    assert sum(result["monthly_ac_kwh"])==pytest.approx(result["raw_ac_kwh"])
    # Existing defect is made explicit, NOT repaired or hidden.
    assert sum(result["monthly_ac_kwh"])>result["annual_ac_kwh"]
    assert result["loss_tree"]["grid_kwh"]==pytest.approx(result["annual_ac_kwh"],abs=0.1)

def test_sqlite_insert_update_delete_and_validation(tmp_path,monkeypatch):
    from suria import storage
    monkeypatch.setattr(storage,"DB_PATH",tmp_path/"projects.db")
    p=sample_project(); i=storage.save_project(p)
    assert storage.load_project(i)==p
    assert storage.save_project(p)==i and len(storage.list_projects())==1
    p["project_notes"]="updated"; assert storage.save_project(p,i)==i
    assert storage.load_project(i)["project_notes"]=="updated"
    bad=copy.deepcopy(p); bad["arrays"][0]["module"]="not supplied"
    with pytest.raises(ValueError): storage.save_project(bad)
    assert len(storage.list_projects())==1
    storage.delete_project(i); assert storage.load_project(i)=={}

def test_streamlit_settings_initial_render():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file(str(ROOT/"src/suria/app.py"),default_timeout=30).run()
    assert not app.exception
    assert any(h.value=="Project Settings" for h in app.header)
    assert any(t.label=="Project name" for t in app.text_input)

def test_layout_corner_containment_limitation_is_visible():
    from suria.layout import estimate_panels_from_polygon
    from shapely.geometry import Polygon
    coords=[[101.69,3.14],[101.6901,3.14],[101.6901,3.1401],[101.69,3.1401],[101.69,3.14]]
    count,_,rects=estimate_panels_from_polygon(coords,2.0,1.0,2.0,0)
    assert count>0
    assert any(not Polygon(coords).covers(Polygon(r)) for r in rects)
