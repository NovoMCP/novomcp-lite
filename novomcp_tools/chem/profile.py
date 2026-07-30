"""Local molecular profile — properties + synthetic accessibility + alerts.

The lite profile is the fully in-process subset of the engine's
`get_molecule_profile`: physicochemical properties, SA score, and RDKit
structural alerts. ADMET prediction and FAVES compliance are engine/service
features and are intentionally NOT part of this package.
"""
from __future__ import annotations

from typing import Any, Dict

from .properties import compute_properties, compute_sa_score, structural_alerts


def molecule_profile(smiles: str, include_alerts: bool = True) -> Dict[str, Any]:
    """Full local profile for one molecule.

    Returns ``{smiles, source, properties, structural_alerts}``. ``properties``
    carries an ``error`` key if the SMILES is invalid.
    """
    props = compute_properties(smiles)
    if "error" not in props:
        sa = compute_sa_score(smiles)
        if sa is not None:
            props["synthetic_accessibility"] = sa
            props["sa_score"] = sa

    out: Dict[str, Any] = {
        "smiles": smiles,
        "source": "computed",
        "in_database": False,
        "properties": props,
    }
    if include_alerts and "error" not in props:
        out["structural_alerts"] = structural_alerts(smiles)
    return out
