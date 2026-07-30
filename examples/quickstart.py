"""novomcp-lite quickstart — library usage in a few lines.

    pip install novomcp-lite
    python examples/quickstart.py
"""
import asyncio

from novomcp_tools import compute_properties, molecule_profile, call_tool
from novomcp_tools.search import search_chembl

ASPIRIN = "CC(=O)OC1=CC=CC=C1C(=O)O"


def main() -> None:
    # 1) Direct library calls — pure RDKit, no network.
    props = compute_properties(ASPIRIN)
    print(f"aspirin  MW={props['molecular_weight']}  logP={props['logp']}  QED={props['qed']}")

    profile = molecule_profile(ASPIRIN)
    print(f"alerts: {profile['structural_alerts']['alert_count']}  SA: {profile['properties']['sa_score']}")

    # 2) The same logic through the tool surface (what the MCP server serves).
    async def _tools() -> None:
        r = await call_tool("calculate_properties", {"smiles": ASPIRIN})
        print("tool calculate_properties ok:", r.success)
        # 3) A public-API search (needs network).
        chembl = await search_chembl("aspirin", top_k=3)
        print("chembl hits:", chembl["total_results"])

    asyncio.run(_tools())


if __name__ == "__main__":
    main()
