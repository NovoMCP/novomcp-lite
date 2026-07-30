"""Live public-API search tests. Marked `network` — skipped in offline CI.

Run with:  pytest -m network
"""
import pytest

from novomcp_tools.search import search_chembl, search_clinical_trials, search_biorxiv

pytestmark = pytest.mark.network


async def test_chembl_compound():
    data = await search_chembl("aspirin", top_k=3)
    assert data["search_type"] == "compound"
    assert data["total_results"] >= 1
    assert any(r.get("smiles") for r in data["results"])


async def test_clinical_trials():
    data = await search_clinical_trials(condition="melanoma", top_k=3)
    assert "trials" in data


async def test_biorxiv():
    data = await search_biorxiv("protein", top_k=3, days_back=90)
    assert "preprints" in data
