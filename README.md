# novomcp-lite

The lightweight, open-source cheminformatics subset of [NovoMCP](https://github.com/NovoMCP/novomcp). Eight zero-config tools — RDKit properties/profiling + public-API search — usable as a **Python library** or over **MCP**. Apache-2.0, ~two dependencies, no orchestration core, no services, no keys.

If all you want is the RDKit tool wrappers and a few public-API searches, this is that — nothing heavier.

```bash
pip install novomcp-lite
```

```python
from novomcp_tools import compute_properties, molecule_profile

compute_properties("CC(=O)OC1=CC=CC=C1C(=O)O")
# {'molecular_weight': 180.159, 'logp': 1.31, 'tpsa': 63.6, 'qed': 0.55,
#  'lipinski_pass': True, ...}

molecule_profile("CC(=O)OC1=CC=CC=C1C(=O)O")
# properties + synthetic-accessibility score + RDKit structural alerts
```

## The tools

| Tool | What it does |
|---|---|
| `calculate_properties` | MW, logP, TPSA, HBD/HBA, QED, Lipinski — in-process RDKit |
| `get_molecule_info` | basic properties + a real synthetic-accessibility (SA) score |
| `get_molecule_profile` | properties + SA + RDKit structural alerts (PAINS/BRENK) |
| `batch_profile` | profile up to 100 molecules at once |
| `screen_library` | screen up to 1000 SMILES; optional Lipinski filter |
| `search_chembl` | ChEMBL compounds / targets / activities (EBI public API) |
| `search_clinical_trials` | ClinicalTrials.gov v2 |
| `search_biorxiv` | bioRxiv / medRxiv preprints |

The five chem tools are fully offline (RDKit only). The three search tools call public APIs — no auth required.

## As an MCP server

```bash
pip install "novomcp-lite[mcp]"
novomcp-lite            # runs an MCP server over stdio
```

Point any MCP client (Claude Desktop, an agent, …) at that command and the eight tools appear. The tool logic is identical to the library.

## What's intentionally *not* here

`novomcp-lite` is the **thin, open subset**. ADMET prediction, docking, molecular dynamics, quantum chemistry, FAVES compliance, the 122M-molecule index, and the autonomous discovery funnel live in the full [NovoMCP engine](https://github.com/NovoMCP/novomcp) and its optional compute services. Lite deliberately carries none of that weight — or its dependencies.

## Relationship to the full engine

This package is the shared, Apache-2.0 foundation: the full engine builds its orchestration on top of the exact same tool logic you get here. One implementation, two products — so lite's numbers always match the engine's.

## Develop

```bash
pip install -e ".[dev]"
pytest -q -m "not network"     # offline chem + registry tests
pytest -m network              # live public-API search tests
```

## Contributing

Issues and PRs welcome — API ergonomics, more RDKit-native tools, packaging. Contributions are under Apache-2.0 (DCO sign-off: `git commit -s`).

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).
