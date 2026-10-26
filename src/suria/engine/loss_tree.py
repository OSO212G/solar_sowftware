"""Canonical HelioScope-format loss tree.

Applies losses in strict order so the waterfall is deterministic and
comparable to HelioScope's published loss tree.

Order:
  Nameplate (POA × η_STC × area × N)
    → Reflection (AOI)
    → Soiling
    → Irradiance (low-light)
    → Temperature
    → Mismatch
    → DC Wiring
    → Bifaciality (gain, negative loss)
    → Front Shading (row-to-row + obstructions + horizon)
    → Inverter Clipping
    → Inverter Efficiency
    → AC System
    → Grid (delivered)

All losses except Temperature, Clipping, and Inverter Efficiency are
*configured* by the user or geometry engine. The three pvlib-internal
losses are extracted from the ModelChain result for diagnostic purposes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass(frozen=True)
class LossEntry:
    """One step in the loss waterfall."""

    pct: float  # signed; negative = gain
    energy_lost_kwh: float
    source: Literal["config", "pvlib", "shading_engine"]
    note: Optional[str] = None


@dataclass
class LossTree:
    """Canonical HelioScope loss waterfall for a single Design."""

    nameplate_kwh: float = 0.0
    reflection: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    soiling: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    irradiance: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    temperature: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "pvlib"))
    mismatch: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    dc_wiring: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    bifaciality: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    front_shading: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "shading_engine"))
    inverter_clipping: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "pvlib"))
    inverter_efficiency: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "pvlib"))
    ac_system: LossEntry = field(default_factory=lambda: LossEntry(0, 0, "config"))
    grid_kwh: float = 0.0

    def _apply(self, energy_kwh: float, entry: LossEntry) -> float:
        """Apply one loss step and return remaining energy."""
        return energy_kwh * (1 - entry.pct / 100)

    def compute(self) -> float:
        """Run the waterfall and set grid_kwh. Returns final energy."""
        e = self.nameplate_kwh
        e = self._apply(e, self.reflection)
        e = self._apply(e, self.soiling)
        e = self._apply(e, self.irradiance)
        e = self._apply(e, self.temperature)
        e = self._apply(e, self.mismatch)
        e = self._apply(e, self.dc_wiring)
        e = self._apply(e, self.bifaciality)
        e = self._apply(e, self.front_shading)
        e = self._apply(e, self.inverter_clipping)
        e = self._apply(e, self.inverter_efficiency)
        e = self._apply(e, self.ac_system)
        self.grid_kwh = e
        return e

    def to_dict(self) -> Dict:
        """Flatten to a dict for reporting / JSON serialization."""
        return {
            "nameplate_kwh": round(self.nameplate_kwh, 1),
            "reflection_pct": round(self.reflection.pct, 2),
            "soiling_pct": round(self.soiling.pct, 2),
            "irradiance_pct": round(self.irradiance.pct, 2),
            "temperature_pct": round(self.temperature.pct, 2),
            "mismatch_pct": round(self.mismatch.pct, 2),
            "dc_wiring_pct": round(self.dc_wiring.pct, 2),
            "bifaciality_pct": round(self.bifaciality.pct, 2),
            "front_shading_pct": round(self.front_shading.pct, 2),
            "inverter_clipping_pct": round(self.inverter_clipping.pct, 2),
            "inverter_efficiency_pct": round(self.inverter_efficiency.pct, 2),
            "ac_system_pct": round(self.ac_system.pct, 2),
            "grid_kwh": round(self.grid_kwh, 1),
        }

    def diagnostic_summary(self) -> List[Dict]:
        """Return a table-friendly list of loss steps."""
        steps = [
            {"step": "Nameplate", "pct": 0.0, "energy_kwh": self.nameplate_kwh, "source": "config"},
            {"step": "Reflection", "pct": self.reflection.pct, "energy_kwh": self._apply(self.nameplate_kwh, self.reflection), "source": self.reflection.source},
            {"step": "Soiling", "pct": self.soiling.pct, "energy_kwh": self._apply(self._apply(self.nameplate_kwh, self.reflection), self.soiling), "source": self.soiling.source},
            {"step": "Irradiance", "pct": self.irradiance.pct, "energy_kwh": 0, "source": self.irradiance.source},
            {"step": "Temperature", "pct": self.temperature.pct, "energy_kwh": 0, "source": self.temperature.source},
            {"step": "Mismatch", "pct": self.mismatch.pct, "energy_kwh": 0, "source": self.mismatch.source},
            {"step": "DC Wiring", "pct": self.dc_wiring.pct, "energy_kwh": 0, "source": self.dc_wiring.source},
            {"step": "Bifaciality", "pct": self.bifaciality.pct, "energy_kwh": 0, "source": self.bifaciality.source},
            {"step": "Front Shading", "pct": self.front_shading.pct, "energy_kwh": 0, "source": self.front_shading.source},
            {"step": "Inverter Clipping", "pct": self.inverter_clipping.pct, "energy_kwh": 0, "source": self.inverter_clipping.source},
            {"step": "Inverter Efficiency", "pct": self.inverter_efficiency.pct, "energy_kwh": 0, "source": self.inverter_efficiency.source},
            {"step": "AC System", "pct": self.ac_system.pct, "energy_kwh": 0, "source": self.ac_system.source},
            {"step": "Grid", "pct": 0.0, "energy_kwh": self.grid_kwh, "source": "final"},
        ]
        # Fill in energy_kwh for each step sequentially
        e = self.nameplate_kwh
        for s in steps[1:-1]:
            e *= (1 - s["pct"] / 100)
            s["energy_kwh"] = round(e, 1)
        return steps
