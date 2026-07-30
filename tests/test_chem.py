"""Offline golden-value tests for the RDKit chem core."""
import pytest

from novomcp_tools.chem import (
    compute_properties,
    compute_sa_score,
    molecule_profile,
    structural_alerts,
)

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"
CAFFEINE = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"


def test_aspirin_properties():
    p = compute_properties(ASPIRIN)
    assert p["molecular_weight"] == pytest.approx(180.159, abs=0.01)
    assert p["logp"] == pytest.approx(1.31, abs=0.02)
    assert p["tpsa"] == pytest.approx(63.6, abs=0.1)
    assert p["hbd"] == 1
    assert p["hba"] == 3
    assert p["qed"] == pytest.approx(0.55, abs=0.02)
    assert p["lipinski_violations"] == 0
    assert p["lipinski_pass"] is True


def test_caffeine_sane():
    p = compute_properties(CAFFEINE)
    assert p["molecular_weight"] == pytest.approx(194.19, abs=0.05)
    assert p["lipinski_pass"] is True


def test_invalid_smiles_returns_error():
    p = compute_properties("not_a_smiles")
    assert "error" in p and "Invalid SMILES" in p["error"]


def test_sa_score():
    sa = compute_sa_score(ASPIRIN)
    assert sa is not None
    assert 1.0 <= sa <= 3.0  # aspirin is easy to make (~1.58)


def test_structural_alerts():
    a = structural_alerts(ASPIRIN)
    assert "alert_count" in a and isinstance(a["alerts"], list)
    # catechol trips a PAINS alert
    c = structural_alerts("Oc1ccccc1O")
    assert c["alert_count"] >= 1


def test_molecule_profile_shape():
    prof = molecule_profile(ASPIRIN)
    assert prof["smiles"] == ASPIRIN
    assert prof["source"] == "computed"
    assert "error" not in prof["properties"]
    assert prof["properties"]["sa_score"] is not None
    assert "structural_alerts" in prof
    # lite profile carries NO compliance / ADMET (engine-only)
    assert "compliance" not in prof
    assert "admet" not in prof
