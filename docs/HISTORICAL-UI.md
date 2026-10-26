# Historical interactive interface — unsupported

The three-step settings → map → results interface remains for source study. The primary demonstration is the offline script in the README. Do not host this application or enter customer data.

Before any local exploration, use a fresh trusted working directory: importing the model creates a relative weather-cache directory and the UI can initialize `projects.db`. Never load cache files from another source; Python pickle can execute code.

For an already prepared environment only, the historical entrypoint is:

```bash
python -m streamlit run SOURCE/src/suria/app.py --server.headless true --server.address 127.0.0.1 --browser.gatherUsageStats false
```

This command is source documentation, not an exercised browser/server recipe in this edition. No UI server was launched. Address queries go to Nominatim; coordinates go to OpenTopoData and PVGIS; map/report imagery uses Esri and browser map dependencies. Availability, terms, attribution and data handling were not requalified. Existing provider attribution strings are retained; no provider assets are bundled.

## Inactive or incomplete controls

- Frame up/wide, module/frame spacing, alignment, surface height and racking choice are stored/displayed but not wired into the active packing/simulation path.
- “Field segments cast shadows” does not implement obstacle-height shadow tracing. Keepout height/setback are not consumed by packing.
- “+ New” and “+ New Keepout” contain placeholder `pass` bodies. “Storage” is not a battery simulation.
- String counts and electrical limits are checked approximately; no automatic MPPT allocation/wiring feature is claimed.
- `layout_portrait` is not a general substitute for the portrait dimension used by layout. Simulation GCR/height uses module width.

## Results and export

Annual energy is after extra losses, but monthly/hourly and mean power profiles are before them. UI labels disclose this. Historical interval arithmetic remains unused in source; it is not displayed as an expected range.

Changing financial widgets recalculates local `fin` and `total_cost`, but PDF export receives the earlier result object. Exported financial assumptions can be stale. CSV is before-extra-loss AC power in W. PDF output is experimental and is not a cleared showcase document. No report or screenshot of this UI is included in the public set.
