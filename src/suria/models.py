"""Shim re-exports for legacy importers.

The canonical domain models live in `suria.domain`.
This file will be removed in a future release.
"""
from suria.domain import (  # noqa: F401
    CartesianFrame,
    ComponentLibrary,
    Design,
    FieldSegment,
    Inverter,
    InverterPlacement,
    Keepout,
    LossAssumptions,
    Module,
    MpptInput,
    Panel,
    Project,
    Site,
    String,
    WeatherSource,
    Wiring,
)
from suria.domain.simulation_input import SimulationInput  # noqa: F401
