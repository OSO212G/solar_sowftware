"""Run retained tests without silently exercising external providers."""
from pathlib import Path
import os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/"src"),str(ROOT/"tools")]
os.environ["MPLBACKEND"]="Agg"
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"]="1"
from offline_demo import deny_network
sys.addaudithook(deny_network)
import pytest
class OfflineSelection:
    def pytest_collection_modifyitems(self, items):
        for item in items:
            if (item.path.name=="test_render.py" and item.name not in {"test_render_map_image_empty","test_payback_chart_bytes"}) or (item.path.name=="test_simulate.py" and item.cls and item.cls.__name__=="TestLossTree"):
                item.add_marker(pytest.mark.skip(reason="Original integration requires live PVGIS/Esri; not authorized. See synthetic offline integration tests."))
raise SystemExit(pytest.main([str(ROOT/"tests"), "-q", "-p", "no:cacheprovider", *sys.argv[1:]], plugins=[OfflineSelection()]))
