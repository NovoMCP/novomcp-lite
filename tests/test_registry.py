"""Offline tests for the tool registry / dispatch."""
import pytest

from novomcp_tools import call_tool, list_tools

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def test_eight_tools_registered():
    names = {t["name"] for t in list_tools()}
    assert names == {
        "calculate_properties",
        "get_molecule_info",
        "get_molecule_profile",
        "batch_profile",
        "screen_library",
        "search_chembl",
        "search_clinical_trials",
        "search_biorxiv",
    }
    for t in list_tools():
        assert t["input_schema"]["type"] == "object"


async def test_calculate_properties():
    r = await call_tool("calculate_properties", {"smiles": ASPIRIN})
    assert r.success
    assert r.data["source"] == "rdkit-local"
    assert r.data["molecular_weight"] == pytest.approx(180.159, abs=0.01)


async def test_get_molecule_info_has_sa():
    r = await call_tool("get_molecule_info", {"smiles": ASPIRIN})
    assert r.success and r.data["sa_score"] is not None


async def test_batch_profile_partial_failure():
    r = await call_tool("batch_profile", {"smiles_list": ["CCO", "CCCO", "bad"]})
    assert r.success
    assert r.data["total"] == 3 and r.data["succeeded"] == 2


async def test_screen_library_lipinski_filter():
    r = await call_tool("screen_library", {"smiles_list": ["CCO", ASPIRIN], "lipinski_only": True})
    assert r.success and r.data["returned"] == 2


async def test_missing_param():
    r = await call_tool("calculate_properties", {})
    assert not r.success and "Missing required parameter" in r.error


async def test_unknown_tool():
    r = await call_tool("does_not_exist", {})
    assert not r.success and "Unknown tool" in r.error
