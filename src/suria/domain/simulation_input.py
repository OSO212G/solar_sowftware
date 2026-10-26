"""Pydantic boundary model for the simulation pipeline.

This model validates the flat dict that simulate_project currently expects.
It is a stepping-stone toward the full Project / Design domain model.
"""
from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SiteInput(BaseModel):
    """Site location for simulation."""
    model_config = ConfigDict(extra="allow")
    name: str = ""
    lat: float
    lon: float
    altitude: float = 0.0


class ArrayInput(BaseModel):
    """One array / field segment for simulation."""
    model_config = ConfigDict(extra="allow")
    name: str = "Array"
    coords: List[List[float]] = []
    polygon_coords: List[List[float]] = []
    panel_rectangles: List[List[List[float]]] = []
    tilt: float = 10.0
    azimuth: float = 180.0
    modules_per_string: int = 1
    strings: int = 1
    module: str
    inverter: str
    shading_loss_pct: float = 2.0
    portrait: bool = False
    setback_m: float = 0.5


class ModuleInput(BaseModel):
    """Module spec as passed from the UI."""
    model_config = ConfigDict(extra="allow")
    name: str
    manufacturer: str = ""
    model: str = ""
    p_max: float
    voc: float = 0.0
    isc: float = 0.0
    vmp: float = 0.0
    imp: float = 0.0
    temp_coeff_pmax: float = 0.0
    temp_coeff_voc: float = 0.0
    temp_coeff_isc: float = 0.0
    noct: float = 45.0
    length: float = 0.0
    width: float = 0.0
    n_s: int = 72
    bifacial: bool = False
    bifaciality: float = 0.0
    cec_name: str = ""


class LossesInput(BaseModel):
    """Configurable loss percentages for simulation."""
    model_config = ConfigDict(extra="allow")
    soiling: float = 2.0
    mismatch: float = 2.0
    wiring: float = 1.5
    availability: float = 1.0
    lid: float = 1.5
    ac_system: float = 0.5
    near_shading: float = 2.0


class InverterInput(BaseModel):
    """Inverter spec as passed from the UI."""
    model_config = ConfigDict(extra="allow")
    name: str
    manufacturer: str = ""
    model: str = ""
    p_aco: float = 0.0
    p_dco: float = 0.0
    v_dco: float = 1.0
    vdcmin: float = 0.0
    vdcmax: float = 0.0
    efficiency: float = 0.98
    cec_name: str = ""
    mppt_count: int = 1
    mppt_min: float = 0.0
    mppt_max: float = 0.0
    mppt_i_max: float = 0.0
    parallel_strings_max: int = 10


class SimulationInput(BaseModel):
    """Validated input for simulate_project."""
    model_config = ConfigDict(extra="allow")
    name: str = "Project"
    customer: str = ""
    designer: str = ""
    project_notes: str = ""
    site: SiteInput
    tariff_block: str = "E1"
    consumer_type: str = "auto"
    fuse_rating_a: float = 0.0
    max_demand_kw: float = 0.0
    arrays: List[ArrayInput]
    module_specs: Dict[str, ModuleInput]
    inverter_specs: Dict[str, InverterInput]
    losses: LossesInput = Field(default_factory=LossesInput)

    @model_validator(mode="after")
    def check_specs_exist(self):
        for arr in self.arrays:
            if arr.module not in self.module_specs:
                raise ValueError(f"Module '{arr.module}' not found in module_specs")
            if arr.inverter not in self.inverter_specs:
                raise ValueError(f"Inverter '{arr.inverter}' not found in inverter_specs")
        return self
