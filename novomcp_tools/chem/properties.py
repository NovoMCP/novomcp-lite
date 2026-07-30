"""In-process molecular properties via RDKit — no network, no services.

Extracted from the NovoMCP engine's in-process property path so the two
share one implementation (the full engine consumes this package). Field
names match the engine's `get_molecule_info` / `calculate_properties`
local output.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# Lazy RDKit contrib SA scorer. The scorer lives in RDKit's contrib tree
# (RDConfig.RDContribDir/SA_Score); import it once on first use.
_SASCORER = None
_ALERT_CATALOG = None


def compute_sa_score(smiles: str) -> Optional[float]:
    """Synthetic accessibility (Ertl & Schuffenhauer), 1 (easy) – 10 (hard).

    Returns None on any failure (bad SMILES, contrib not importable).
    """
    global _SASCORER
    try:
        from rdkit import Chem

        if _SASCORER is None:
            import os
            import sys

            from rdkit.Chem import RDConfig

            sa_dir = os.path.join(RDConfig.RDContribDir, "SA_Score")
            if sa_dir not in sys.path:
                sys.path.append(sa_dir)
            import sascorer  # type: ignore

            _SASCORER = sascorer
        mol = Chem.MolFromSmiles(smiles or "")
        if mol is None:
            return None
        return round(_SASCORER.calculateScore(mol), 2)
    except Exception:
        return None


def compute_properties(smiles: str) -> Dict[str, Any]:
    """Basic physicochemical properties + drug-likeness for one SMILES.

    Returns a dict of properties, or ``{"error": ...}`` on a bad SMILES or
    missing RDKit — the caller decides how to surface it (matches the
    engine's in-process contract).
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import Crippen, Descriptors, Lipinski, QED, rdMolDescriptors
    except ImportError:
        return {"error": "RDKit not installed — pip install rdkit"}

    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        tpsa = Descriptors.TPSA(mol)
        hbd = Lipinski.NumHDonors(mol)
        hba = Lipinski.NumHAcceptors(mol)
        rot_bonds = Lipinski.NumRotatableBonds(mol)
        aromatic_rings = rdMolDescriptors.CalcNumAromaticRings(mol)
        heavy_atoms = mol.GetNumHeavyAtoms()

        # Lipinski Rule-of-Five violations
        lipinski_violations = sum([mw > 500, logp > 5, hbd > 5, hba > 10])

        try:
            qed_score: Optional[float] = QED.qed(mol)
        except Exception:
            qed_score = None

        return {
            "molecular_weight": round(mw, 3),
            "exact_mass": round(Descriptors.ExactMolWt(mol), 4),
            "logp": round(logp, 3),
            "tpsa": round(tpsa, 2),
            "hbd": hbd,
            "hba": hba,
            "rotatable_bonds": rot_bonds,
            "aromatic_rings": aromatic_rings,
            "heavy_atoms": heavy_atoms,
            "qed": round(qed_score, 3) if qed_score is not None else None,
            "lipinski_violations": lipinski_violations,
            "lipinski_pass": lipinski_violations == 0,
        }
    except Exception as e:  # noqa: BLE001 — surface any RDKit failure as data
        return {"error": str(e)}


def structural_alerts(smiles: str) -> Dict[str, Any]:
    """Structural-alert screen using RDKit's PAINS + BRENK filter catalogs.

    Pure RDKit, no external data. Returns ``{alert_count, alerts: [...]}`` or
    ``{"error": ...}``. (This is a lite-native local screen; the full engine's
    curated alert set for known molecules is a separate, service-backed path.)
    """
    global _ALERT_CATALOG
    try:
        from rdkit import Chem
        from rdkit.Chem import FilterCatalog
        from rdkit.Chem.FilterCatalog import FilterCatalogParams
    except ImportError:
        return {"error": "RDKit not installed — pip install rdkit"}

    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return {"error": f"Invalid SMILES: {smiles}"}

        if _ALERT_CATALOG is None:
            params = FilterCatalogParams()
            params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
            params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
            _ALERT_CATALOG = FilterCatalog.FilterCatalog(params)

        alerts = []
        for match in _ALERT_CATALOG.GetMatches(mol):
            try:
                catalog = match.GetProp("FilterSet")
            except Exception:
                catalog = None
            alerts.append({"name": match.GetDescription(), "catalog": catalog})
        return {"alert_count": len(alerts), "alerts": alerts}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}
