# Known limitations

## Energy branches and diagnostics

Annual energy applies soiling → mismatch → wiring → availability → LID → AC-system → near-shading factors sequentially to shaded ModelChain AC. Monthly/hourly and daily mean power omit these extra factors. This inherited inconsistency is characterized, not repaired.

The separate loss tree is an experimental diagnostic sketch. `availability` and `lid` are assigned dynamically but are not declared/applied by `LossTree.compute()`. Its starting nameplate energy already uses shaded POA, then front shading is applied again. Temperature is estimated from mean cell temperature; clipping operates on the DC result rather than selecting only its power column. These are not controlled energy-difference experiments. Project aggregation copies selected percentages, sets `grid_kwh` from annual output and omits the per-array diagnostic table. Neither that assignment nor an empty report table reconciles the model.

Bifacial ratios are clipped at one and scale a front-side base; an independently validated rear-energy contribution is not established. Equipment CEC lookup can silently fall back to manual approximations. The offline fixture clears CEC names deliberately. CSV data used by the UI and JSON/domain equipment data disagree in places and are not interchangeable authorities; datasheet accuracy is unqualified.

## Time and geometry

- Energy summation assumes one-hour samples; capacity factor assumes 8,760 hours. Completeness, arbitrary intervals and leap-year integration are not validated.
- Array hourly results are combined by position, without timestamp-equality checks. Daily grouping uses the weather index's hour; a `Location` timezone does not convert that index. The synthetic fixture explicitly uses Asia/Kuala_Lumpur; live provider timestamps were not qualified.
- Longitude rounding is not an IANA geographic/civil timezone resolver. Its tests characterize the approximation, not Malaysian civil time.
- Packing tests panel centers. Corners can cross the boundary or overlap keepouts. Row pitch below a panel footprint can permit overlap; nonpositive increments can prevent loop progress. Use bounded positive examples only.
- Row-spacing geometry is not a site/date-specific winter-solstice shading calculation. Simulation's module-width GCR/height choice can differ from portrait-dependent layout dimensions. Keepout heights and setbacks do not trace shadows.
- GeoJSON interior rings are treated as separate usable polygons, not holes.

## State and migration

The active simulation and persistence use flat dictionaries. `domain/converter.py` is a partial bridge: stringing/inverter assignments and full assumptions are not preserved losslessly. Panel-bearing UI integer/default segment IDs may fail the domain UUID contract. This route is not a completed canonical migration.

Same-name saves overwrite; updating an unknown SQLite ID can return that ID without updating a row. There is no multi-user ownership/access isolation. Financial widget recalculation does not update the result object passed to PDF export; displayed and exported scenarios can differ. [Inactive controls](HISTORICAL-UI.md) are retained, not implemented.

## Financial and electrical interpretation

Fixed tariff/export rates, assumed self-consumption and degradation are illustrative historical inputs, not current policy or eligibility guidance. There is no consumption trace, operating cost, replacements, financing, discounting or changing-tariff model. Twenty-five-year benefit is gross modeled benefit, not net profit. Electrical checks and indicative BOM do not replace a site survey, protection design or qualified engineering review.

## Trust boundary

The relative weather cache uses `pickle.load`: an untrusted file may execute code before an exception is caught. No pre-existing cache is distributed. Use a fresh trusted CWD. The engine suppresses warnings globally; silence is not numerical validity. User text is interpolated into unsafe HTML/popups without consistent escaping; fixed upload temporary names and partially sanitized report paths are not safe multi-user service boundaries.

Live PVGIS, Nominatim, OpenTopoData, Esri and browser map integrations were not exercised or requalified. Queries/locations can leave the machine. The Python offline audit hook is cooperative test scaffolding, not an OS sandbox or a guard for browser JavaScript. No customer data, hardware, hosted/concurrent operation, safety/regulatory acceptance or current tariffs were tested.
