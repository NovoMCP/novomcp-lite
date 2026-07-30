"""ChEMBL search via the public EBI API — no key required.

https://www.ebi.ac.uk/chembl/api/data/
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


async def _get_with_retry(client: httpx.AsyncClient, url: str, retries: int = 3) -> httpx.Response:
    """GET with exponential backoff on transient upstream failures.

    The EBI ChEMBL API is occasionally flaky (5xx / timeouts); retry a few
    times, then surface the error unchanged — no fallback data.
    """
    delay = 0.5
    response = None
    for attempt in range(retries):
        try:
            response = await client.get(url)
            if response.status_code >= 500 and attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < retries - 1:
                await asyncio.sleep(delay)
                delay *= 2
                continue
            raise
    assert response is not None
    response.raise_for_status()
    return response


async def search_chembl(query: str, search_type: str = "compound", top_k: int = 10) -> Dict[str, Any]:
    """Search ChEMBL for compounds, targets, or bioactivities.

    search_type: "compound" | "target" | "activity". Returns a dict with
    `results`. Raises on a bad upstream response (no fabricated data).
    """
    if not query:
        raise ValueError("Missing required parameter: query")
    top_k = min(top_k, 25)
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        if search_type == "compound":
            url = f"{BASE_URL}/molecule/search.json?q={query}&limit={top_k}"
            data = (await _get_with_retry(client, url)).json()
            for mol in data.get("molecules", []):
                mol_props = mol.get("molecule_properties") or {}
                mol_struct = mol.get("molecule_structures") or {}
                results.append(
                    {
                        "chembl_id": mol.get("molecule_chembl_id"),
                        "name": mol.get("pref_name"),
                        "molecule_type": mol.get("molecule_type"),
                        "max_phase": mol.get("max_phase"),
                        "molecular_formula": mol_props.get("full_molformula"),
                        "molecular_weight": mol_props.get("full_mwt"),
                        "smiles": mol_struct.get("canonical_smiles"),
                        "first_approval": mol.get("first_approval"),
                        "oral": mol.get("oral"),
                        "indication_class": mol.get("indication_class"),
                    }
                )
        elif search_type == "target":
            url = f"{BASE_URL}/target/search.json?q={query}&limit={top_k}"
            data = (await _get_with_retry(client, url)).json()
            for target in data.get("targets", []):
                results.append(
                    {
                        "chembl_id": target.get("target_chembl_id"),
                        "name": target.get("pref_name"),
                        "target_type": target.get("target_type"),
                        "organism": target.get("organism"),
                        "target_components": [
                            {"accession": c.get("accession"), "description": c.get("component_description")}
                            for c in (target.get("target_components") or [])[:3]
                        ],
                    }
                )
        elif search_type == "activity":
            url = f"{BASE_URL}/activity/search.json?q={query}&limit={top_k}"
            data = (await _get_with_retry(client, url)).json()
            for activity in data.get("activities", []):
                results.append(
                    {
                        "activity_id": activity.get("activity_id"),
                        "molecule_chembl_id": activity.get("molecule_chembl_id"),
                        "target_chembl_id": activity.get("target_chembl_id"),
                        "target_name": activity.get("target_pref_name"),
                        "assay_type": activity.get("assay_type"),
                        "standard_type": activity.get("standard_type"),
                        "standard_value": activity.get("standard_value"),
                        "standard_units": activity.get("standard_units"),
                        "pchembl_value": activity.get("pchembl_value"),
                    }
                )
        else:
            raise ValueError(f"Unknown search_type: {search_type!r} (use compound|target|activity)")

    return {
        "query": query,
        "search_type": search_type,
        "total_results": len(results),
        "results": results,
    }
