"""Converter between flat session-state dicts and the domain model.

This is the migration bridge: the UI still works with flat dicts,
but the simulation engine and storage will gradually move to the
Project / Design / FieldSegment hierarchy.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from suria.domain import (
    CartesianFrame,
    ComponentLibrary,
    Design,
    FieldSegment,
    Inverter,
    Keepout,
    LossAssumptions,
    Module,
    Panel,
    Project,
    Site,
    Wiring,
)
from suria.domain.frame import make_frame, polygon_to_xy, to_xy


def _module_from_flat(spec: dict) -> Module:
    return Module(
        name=spec["name"],
        manufacturer=spec.get("manufacturer", ""),
        model=spec.get("model", ""),
        p_max=spec["p_max"],
        voc=spec.get("voc", 0.0),
        isc=spec.get("isc", 0.0),
        vmp=spec.get("vmp", 0.0),
        imp=spec.get("imp", 0.0),
        temp_coeff_pmax=spec.get("temp_coeff_pmax", 0.0),
        temp_coeff_voc=spec.get("temp_coeff_voc", 0.0),
        temp_coeff_isc=spec.get("temp_coeff_isc", 0.0),
        noct=spec.get("noct", 45.0),
        length=spec.get("length", 0.0),
        width=spec.get("width", 0.0),
        n_s=spec.get("n_s", 72),
        bifacial=spec.get("bifacial", False),
        bifaciality=spec.get("bifaciality", 0.0),
        cec_name=spec.get("cec_name", ""),
    )


def _inverter_from_flat(spec: dict) -> Inverter:
    return Inverter(
        name=spec["name"],
        manufacturer=spec.get("manufacturer", ""),
        model=spec.get("model", ""),
        p_aco_w=spec.get("p_aco", 0.0),
        p_dco_w=spec.get("p_dco", 0.0),
        v_dco_v=spec.get("v_dco", 0.0),
        vdcmin_v=spec.get("vdcmin", 0.0),
        vdcmax_v=spec.get("vdcmax", 0.0),
        efficiency=spec.get("efficiency", 0.98),
        cec_name=spec.get("cec_name", ""),
    )


def _panels_from_flat(
    array: dict, frame: CartesianFrame
) -> Tuple[List[Panel], List[List[Tuple[float, float]]]]:
    """Build Panel objects from panel_rectangles in the flat dict.

    Returns (panels, polygons_xy) where polygons_xy is the list of
    4-corner polygons in frame-local metres.
    """
    panels: List[Panel] = []
    polygons_xy: List[List[Tuple[float, float]]] = []
    segment_id = array.get("id", "array-0")
    for rect in array.get("panel_rectangles", []):
        if not rect:
            continue
        corners_latlon = [(c[0], c[1]) for c in rect]
        corners_xy = [to_xy(frame, lon, lat) for lon, lat in corners_latlon]
        polygons_xy.append(corners_xy)
        cx = sum(x for x, _ in corners_xy) / 4.0
        cy = sum(y for _, y in corners_xy) / 4.0
        panels.append(
            Panel(
                segment_id=segment_id,
                centroid_xy=(cx, cy),
                corners_xy=corners_xy,
            )
        )
    return panels, polygons_xy


def _field_segment_from_flat(array: dict, frame: CartesianFrame) -> FieldSegment:
    coords = array.get("coords", [])
    polygon_xy = polygon_to_xy(frame, coords) if coords else []

    panels, _ = _panels_from_flat(array, frame)

    return FieldSegment(
        name=array.get("name", "Array"),
        polygon_xy=polygon_xy,
        tilt_deg=array.get("tilt", 10.0),
        azimuth_deg=array.get("azimuth", 180.0),
        module_ref=array.get("module", ""),
        setback_m=array.get("setback_m", 0.5),
        row_spacing_m=array.get("row_spacing_m", None),
        portrait=array.get("portrait", False),
        panels=panels,
        shading_loss_pct=array.get("shading_loss_pct", 2.0),
    )


def _keepouts_from_flat(array: dict, frame: CartesianFrame) -> List[Keepout]:
    keepouts: List[Keepout] = []
    for k in array.get("keepouts", []):
        coords = k.get("coords", [])
        polygon_xy = polygon_to_xy(frame, coords) if coords else []
        keepouts.append(
            Keepout(
                name=k.get("name", "Keepout"),
                polygon_xy=polygon_xy,
                height_m=k.get("height_m", 0.0),
                setback_m=k.get("setback_m", 0.0),
                active=k.get("active", True),
            )
        )
    return keepouts


def flat_to_project(data: dict) -> Project:
    """Convert a flat session-state project dict to a domain Project."""
    site_data = data.get("site", {})
    site = Site(
        name=site_data.get("name", ""),
        lat=site_data.get("lat", 0.0),
        lon=site_data.get("lon", 0.0),
        altitude=site_data.get("altitude", 0.0),
    )

    frame = make_frame(site.lat, site.lon)

    # Build component library
    modules = {
        k: _module_from_flat(v) for k, v in data.get("module_specs", {}).items()
    }
    inverters = {
        k: _inverter_from_flat(v) for k, v in data.get("inverter_specs", {}).items()
    }
    library = ComponentLibrary(modules=modules, inverters=inverters)

    # Build design
    segments: List[FieldSegment] = []
    keepouts: List[Keepout] = []
    for arr in data.get("arrays", []):
        segments.append(_field_segment_from_flat(arr, frame))
        keepouts.extend(_keepouts_from_flat(arr, frame))

    design = Design(
        name="Design 1",
        frame=frame,
        field_segments=segments,
        keepouts=keepouts,
        losses=LossAssumptions(),
        wiring=Wiring(),
    )

    return Project(
        name=data.get("name", "Project"),
        customer=data.get("customer", ""),
        designer=data.get("designer", ""),
        site=site,
        designs=[design],
        component_library=library,
    )


def project_to_flat(project: Project) -> dict:
    """Convert a domain Project back to the flat dict the UI expects.

    This is lossy: panel-level detail and domain-only fields are flattened.
    """
    if not project.designs:
        raise ValueError("Project has no designs")
    design = project.designs[0]
    frame = design.frame
    if frame is None:
        raise ValueError("Design has no CartesianFrame")

    from suria.domain.frame import polygon_to_latlon

    # Flatten arrays from field segments
    arrays: List[dict] = []
    for seg in design.field_segments:
        arrays.append({
            "name": seg.name,
            "coords": polygon_to_latlon(frame, seg.polygon_xy),
            "tilt": seg.tilt_deg,
            "azimuth": seg.azimuth_deg,
            "modules_per_string": 20,  # default — not stored in FieldSegment yet
            "strings": 1,
            "module": seg.module_ref,
            "setback_m": seg.setback_m,
            "row_spacing_m": seg.row_spacing_m,
            "portrait": seg.portrait,
            "shading_loss_pct": seg.shading_loss_pct,
            "panel_rectangles": [
                [[lon, lat] for lon, lat in polygon_to_latlon(frame, p.corners_xy)]
                for p in seg.panels
            ],
        })

    # Flatten module / inverter specs
    module_specs: Dict[str, dict] = {}
    for name, mod in (project.component_library.modules if project.component_library else {}).items():
        module_specs[name] = {
            "name": mod.name,
            "manufacturer": mod.manufacturer,
            "model": mod.model,
            "p_max": mod.p_max,
            "voc": mod.voc,
            "isc": mod.isc,
            "vmp": mod.vmp,
            "imp": mod.imp,
            "temp_coeff_pmax": mod.temp_coeff_pmax,
            "temp_coeff_voc": mod.temp_coeff_voc,
            "temp_coeff_isc": mod.temp_coeff_isc,
            "noct": mod.noct,
            "length": mod.length,
            "width": mod.width,
            "n_s": mod.n_s,
            "bifacial": mod.bifacial,
            "bifaciality": mod.bifaciality,
            "cec_name": mod.cec_name,
        }

    inverter_specs: Dict[str, dict] = {}
    for name, inv in (project.component_library.inverters if project.component_library else {}).items():
        inverter_specs[name] = {
            "name": inv.name,
            "manufacturer": inv.manufacturer,
            "model": inv.model,
            "p_aco": inv.p_aco_w,
            "p_dco": inv.p_dco_w,
            "v_dco": inv.v_dco_v,
            "vdcmin": inv.vdcmin_v,
            "vdcmax": inv.vdcmax_v,
            "efficiency": inv.efficiency,
            "cec_name": inv.cec_name,
        }

    return {
        "name": project.name,
        "customer": project.customer,
        "designer": project.designer,
        "site": {
            "name": project.site.name,
            "lat": project.site.lat,
            "lon": project.site.lon,
            "altitude": project.site.altitude,
        },
        "arrays": arrays,
        "module_specs": module_specs,
        "inverter_specs": inverter_specs,
    }
