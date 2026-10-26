"""Component library loading — CSV/JSON to Pydantic models."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import pandas as pd

from suria.domain import Inverter, Module


def _safe_str(val) -> str:
    """Return empty string for NaN/None, otherwise str."""
    if pd.isna(val):
        return ""
    return str(val)


def _safe_float(val, default: float = 0.0) -> float:
    if pd.isna(val):
        return default
    return float(val)


def _safe_bool(val) -> bool:
    if pd.isna(val):
        return False
    return bool(val)


def load_modules_csv(path: Path) -> Dict[str, Module]:
    """Load modules from CSV and return as name → Module dict."""
    df = pd.read_csv(path)
    modules = {}
    for _, row in df.iterrows():
        modules[row["name"]] = Module(
            name=row["name"],
            manufacturer=_safe_str(row.get("manufacturer")),
            model=_safe_str(row.get("model")),
            p_max=_safe_float(row["p_max"]),
            voc=_safe_float(row["voc"]),
            isc=_safe_float(row["isc"]),
            vmp=_safe_float(row["vmp"]),
            imp=_safe_float(row["imp"]),
            temp_coeff_pmax=_safe_float(row["temp_coeff_pmax"]),
            temp_coeff_voc=_safe_float(row["temp_coeff_voc"]),
            temp_coeff_isc=_safe_float(row["temp_coeff_isc"]),
            noct=_safe_float(row["noct"]),
            length=_safe_float(row["length"]),
            width=_safe_float(row["width"]),
            n_s=int(_safe_float(row.get("n_s"), 72)),
            bifacial=_safe_bool(row.get("bifacial")),
            bifaciality=_safe_float(row.get("bifaciality"), 0.0),
            cec_name=_safe_str(row.get("cec_name")),
        )
    return modules


def load_inverters_csv(path: Path) -> Dict[str, Inverter]:
    """Load inverters from CSV and return as name → Inverter dict.

    For backward compatibility, CSV inverters without explicit MPPT inputs
    are treated as single-MPPT devices.
    """
    df = pd.read_csv(path)
    inverters = {}
    for _, row in df.iterrows():
        mppt_inputs = []
        mppt_count = int(_safe_float(row.get("mppt_count"), 1))
        v_dco = _safe_float(row.get("v_dco"), 1.0)
        for i in range(1, mppt_count + 1):
            from suria.domain import MpptInput

            mppt_inputs.append(
                MpptInput(
                    index=i,
                    v_min_v=_safe_float(row.get("mppt_min"), _safe_float(row.get("vdcmin"))),
                    v_max_v=_safe_float(row.get("mppt_max"), _safe_float(row.get("vdcmax"))),
                    i_max_a=_safe_float(row.get("mppt_i_max"), _safe_float(row.get("p_dco"), 0) / v_dco if v_dco else 0),
                    parallel_strings_max=int(_safe_float(row.get("parallel_strings_max"), 10)),
                )
            )
        inverters[row["name"]] = Inverter(
            name=row["name"],
            manufacturer=_safe_str(row.get("manufacturer")),
            model=_safe_str(row.get("model")),
            p_aco_w=_safe_float(row["p_aco"]),
            p_dco_w=_safe_float(row["p_dco"]),
            v_dco_v=v_dco,
            vdcmin_v=_safe_float(row["vdcmin"]),
            vdcmax_v=_safe_float(row["vdcmax"]),
            efficiency=_safe_float(row.get("efficiency"), 0.98),
            cec_name=_safe_str(row.get("cec_name")),
            mppt_inputs=mppt_inputs,
        )
    return inverters


def save_component_library_json(modules: Dict[str, Module], inverters: Dict[str, Inverter], path: Path) -> None:
    """Save a component library to JSON."""
    payload = {
        "modules": {k: v.dict() for k, v in modules.items()},
        "inverters": {k: v.dict() for k, v in inverters.items()},
    }
    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)


def load_component_library_json(path: Path) -> tuple[Dict[str, Module], Dict[str, Inverter]]:
    """Load a component library from JSON."""
    with open(path) as f:
        payload = json.load(f)
    modules = {k: Module(**v) for k, v in payload.get("modules", {}).items()}
    inverters = {k: Inverter(**v) for k, v in payload.get("inverters", {}).items()}
    return modules, inverters
