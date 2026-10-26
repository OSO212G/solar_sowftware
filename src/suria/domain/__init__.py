"""Suria domain models — HelioScope-class data model."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Racking(str, Enum):
    FIXED_TILT = "fixed_tilt"
    FLUSH_MOUNT = "flush_mount"
    GROUND_MOUNT = "ground_mount"
    EAST_WEST = "east_west"
    CARPORT = "carport"
    SINGLE_AXIS_TRACKER = "single_axis_tracker"


class CartesianFrame(BaseModel):
    """Frozen local Cartesian frame for a Design."""

    model_config = ConfigDict(frozen=True)

    origin_lat: float
    origin_lon: float
    utm_epsg: int
    rotation_deg: float = 0.0


class Site(BaseModel):
    """Project site location."""

    name: str
    lat: float
    lon: float
    altitude: float = 0.0


class Panel(BaseModel):
    """A single PV panel inside a FieldSegment."""

    id: UUID = Field(default_factory=uuid4)
    segment_id: UUID
    centroid_xy: Tuple[float, float]
    corners_xy: List[Tuple[float, float]]
    string_id: Optional[UUID] = None


class Keepout(BaseModel):
    """Obstruction zone inside a Design."""

    id: UUID = Field(default_factory=uuid4)
    name: str = "Keepout"
    polygon_xy: List[Tuple[float, float]]
    height_m: float = 0.0
    setback_m: float = 0.0
    active: bool = True


class String(BaseModel):
    """A DC string connecting panels to an MPPT input."""

    id: UUID = Field(default_factory=uuid4)
    panel_ids: List[UUID] = []
    home_run_m: float = 0.0


class MpptInput(BaseModel):
    """One MPPT channel on an inverter."""

    index: int
    strings: List[String] = []
    v_min_v: float
    v_max_v: float
    i_max_a: float
    parallel_strings_max: int


class InverterPlacement(BaseModel):
    """An inverter placed at a location in the Design."""

    id: UUID = Field(default_factory=uuid4)
    inverter_ref: str
    location_xy: Optional[Tuple[float, float]] = None
    mppt_inputs: List[MpptInput] = []


class Wiring(BaseModel):
    """DC/AC wiring assumptions for a Design."""

    dc_conductor_awg: int = 10
    ac_conductor_awg: int = 10
    target_voltage_drop_pct: float = 2.0


class LossAssumptions(BaseModel):
    """Configurable loss percentages for a Design."""

    soiling: float = 2.0
    mismatch: float = 2.0
    dc_wiring: float = 1.5
    availability: float = 1.0
    lid: float = 1.5
    ac_system: float = 0.5


class WeatherSource(BaseModel):
    """Weather data source for simulation."""

    type: str = "pvgis"  # pvgis | nasa_power | upload_csv
    params: dict = {}


class FieldSegment(BaseModel):
    """A roof or ground area containing panels."""

    id: UUID = Field(default_factory=uuid4)
    name: str = "Segment"
    polygon_xy: List[Tuple[float, float]] = []
    tilt_deg: float = 10.0
    azimuth_deg: float = 180.0
    racking: Racking = Racking.FIXED_TILT
    module_ref: str = ""
    setback_m: float = 0.5
    row_spacing_m: Optional[float] = None
    portrait: bool = False
    panels: List[Panel] = []
    shading_loss_pct: float = 2.0  # near-shading until Phase D replaces it


class Design(BaseModel):
    """One design (variant) inside a Project."""

    id: UUID = Field(default_factory=uuid4)
    name: str = "Design 1"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    parent_design_id: Optional[UUID] = None
    frame: Optional[CartesianFrame] = None
    field_segments: List[FieldSegment] = []
    keepouts: List[Keepout] = []
    inverters: List[InverterPlacement] = []
    wiring: Wiring = Field(default_factory=Wiring)
    losses: LossAssumptions = Field(default_factory=LossAssumptions)
    weather: WeatherSource = Field(default_factory=WeatherSource)


class Project(BaseModel):
    """Top-level project containing designs."""

    id: UUID = Field(default_factory=uuid4)
    name: str = "Project"
    customer: str = ""
    designer: str = ""
    site: Site
    designs: List[Design] = []
    component_library: Optional["ComponentLibrary"] = None


# --- Component library models ---


class Module(BaseModel):
    """PV module specification."""

    name: str
    manufacturer: str = ""
    model: str = ""
    p_max: float
    voc: float
    isc: float
    vmp: float
    imp: float
    temp_coeff_pmax: float
    temp_coeff_voc: float
    temp_coeff_isc: float
    noct: float
    length: float
    width: float
    n_s: int = 72
    bifacial: bool = False
    bifaciality: float = 0.0
    cec_name: str = ""


class Inverter(BaseModel):
    """Inverter specification with multi-MPPT support."""

    name: str
    manufacturer: str = ""
    model: str = ""
    p_aco_w: float
    p_dco_w: float
    v_dco_v: float
    vdcmin_v: float
    vdcmax_v: float
    efficiency: float = 0.98
    cec_name: str = ""
    mppt_inputs: List[MpptInput] = []  # if empty, single implicit MPPT


class ComponentLibrary(BaseModel):
    """All reusable components for a project."""

    modules: dict[str, Module] = {}
    inverters: dict[str, Inverter] = {}


# Rebuild forward refs
Project.model_rebuild()
