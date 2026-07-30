"""The novomcp-lite tool registry.

Eight zero-config tools — five RDKit cheminformatics + three public-API
searches — each with a JSON-Schema input and an async handler returning a
``ToolResult``. This registry is the single surface both the library helpers
and the (optional) MCP server share; it mirrors the engine's tool contract so
the full engine can consume this package.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from .chem import compute_properties, compute_sa_score, molecule_profile
from .search import search_biorxiv, search_chembl, search_clinical_trials


@dataclass
class ToolResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class Tool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Awaitable[ToolResult]]


def _require(args: Dict[str, Any], key: str) -> Any:
    val = args.get(key)
    if val in (None, ""):
        raise ValueError(f"Missing required parameter: {key}")
    return val


# --------------------------------------------------------------------------
# Handlers
# --------------------------------------------------------------------------
async def _h_calculate_properties(args: Dict[str, Any]) -> ToolResult:
    smiles = _require(args, "smiles")
    props = compute_properties(smiles)
    if "error" in props:
        return ToolResult(False, error=props["error"])
    return ToolResult(True, {"smiles": smiles, "source": "rdkit-local", **props})


async def _h_get_molecule_info(args: Dict[str, Any]) -> ToolResult:
    smiles = _require(args, "smiles")
    props = compute_properties(smiles)
    if "error" in props:
        return ToolResult(False, error=props["error"])
    sa = compute_sa_score(smiles)
    if sa is not None:
        props["synthetic_accessibility"] = sa
        props["sa_score"] = sa
    return ToolResult(True, {"smiles": smiles, **props})


async def _h_get_molecule_profile(args: Dict[str, Any]) -> ToolResult:
    smiles = _require(args, "smiles")
    prof = molecule_profile(smiles, include_alerts=args.get("include_alerts", True))
    if "error" in prof["properties"]:
        return ToolResult(False, error=prof["properties"]["error"])
    return ToolResult(True, prof)


async def _h_batch_profile(args: Dict[str, Any]) -> ToolResult:
    smiles_list = _require(args, "smiles_list")
    if not isinstance(smiles_list, list):
        return ToolResult(False, error="smiles_list must be a list of SMILES strings")
    smiles_list = smiles_list[:100]
    profiles = [molecule_profile(s, include_alerts=args.get("include_alerts", False)) for s in smiles_list]
    ok = sum(1 for p in profiles if "error" not in p["properties"])
    return ToolResult(True, {"total": len(profiles), "succeeded": ok, "profiles": profiles})


async def _h_screen_library(args: Dict[str, Any]) -> ToolResult:
    smiles_list = _require(args, "smiles_list")
    if not isinstance(smiles_list, list):
        return ToolResult(False, error="smiles_list must be a list of SMILES strings")
    smiles_list = smiles_list[:1000]
    lipinski_only = bool(args.get("lipinski_only", False))
    rows = []
    for s in smiles_list:
        props = compute_properties(s)
        if "error" in props:
            rows.append({"smiles": s, "error": props["error"]})
            continue
        if lipinski_only and not props.get("lipinski_pass"):
            continue
        rows.append({"smiles": s, **props})
    passed = sum(1 for r in rows if "error" not in r and r.get("lipinski_pass"))
    return ToolResult(True, {"total_screened": len(smiles_list), "returned": len(rows),
                             "lipinski_pass": passed, "results": rows})


async def _h_search_chembl(args: Dict[str, Any]) -> ToolResult:
    try:
        data = await search_chembl(
            _require(args, "query"),
            search_type=args.get("search_type", "compound"),
            top_k=args.get("top_k", 10),
        )
        return ToolResult(True, data)
    except Exception as e:  # noqa: BLE001
        return ToolResult(False, error=f"ChEMBL search failed: {e}")


async def _h_search_clinical_trials(args: Dict[str, Any]) -> ToolResult:
    try:
        data = await search_clinical_trials(
            query=args.get("query"),
            condition=args.get("condition"),
            status=args.get("status") or "ALL",
            phase=args.get("phase") or "ALL",
            top_k=args.get("top_k", 10),
        )
        return ToolResult(True, data)
    except Exception as e:  # noqa: BLE001
        return ToolResult(False, error=f"Clinical trials search failed: {e}")


async def _h_search_biorxiv(args: Dict[str, Any]) -> ToolResult:
    try:
        data = await search_biorxiv(
            _require(args, "query"),
            server=args.get("server", "biorxiv"),
            top_k=args.get("top_k", 10),
            days_back=args.get("days_back", 180),
        )
        return ToolResult(True, data)
    except Exception as e:  # noqa: BLE001
        return ToolResult(False, error=f"bioRxiv search failed: {e}")


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
_S = {"type": "string"}

TOOLS: List[Tool] = [
    Tool("calculate_properties",
         "Physicochemical properties + drug-likeness (MW, logP, TPSA, HBD/HBA, QED, Lipinski) for one SMILES, computed in-process via RDKit.",
         {"type": "object", "required": ["smiles"], "properties": {"smiles": _S}},
         _h_calculate_properties),
    Tool("get_molecule_info",
         "Basic RDKit properties plus a real synthetic-accessibility (SA) score for one SMILES.",
         {"type": "object", "required": ["smiles"], "properties": {"smiles": _S}},
         _h_get_molecule_info),
    Tool("get_molecule_profile",
         "Full local profile for one molecule: properties + SA score + RDKit structural alerts (PAINS/BRENK).",
         {"type": "object", "required": ["smiles"],
          "properties": {"smiles": _S, "include_alerts": {"type": "boolean", "default": True}}},
         _h_get_molecule_profile),
    Tool("batch_profile",
         "Profile up to 100 molecules at once (properties + SA per molecule).",
         {"type": "object", "required": ["smiles_list"],
          "properties": {"smiles_list": {"type": "array", "items": _S, "maxItems": 100},
                         "include_alerts": {"type": "boolean", "default": False}}},
         _h_batch_profile),
    Tool("screen_library",
         "Screen up to 1000 SMILES on physicochemical properties; optionally return only Lipinski-passing molecules.",
         {"type": "object", "required": ["smiles_list"],
          "properties": {"smiles_list": {"type": "array", "items": _S, "maxItems": 1000},
                         "lipinski_only": {"type": "boolean", "default": False}}},
         _h_screen_library),
    Tool("search_chembl",
         "Search ChEMBL (EBI public API) for compounds, targets, or bioactivities.",
         {"type": "object", "required": ["query"],
          "properties": {"query": _S,
                         "search_type": {"type": "string", "enum": ["compound", "target", "activity"], "default": "compound"},
                         "top_k": {"type": "integer", "default": 10}}},
         _h_search_chembl),
    Tool("search_clinical_trials",
         "Search ClinicalTrials.gov (public API v2) by free-text query and/or condition, with optional status/phase filters.",
         {"type": "object",
          "properties": {"query": _S, "condition": _S,
                         "status": {"type": "string", "default": "ALL"},
                         "phase": {"type": "string", "default": "ALL"},
                         "top_k": {"type": "integer", "default": 10}}},
         _h_search_clinical_trials),
    Tool("search_biorxiv",
         "Search bioRxiv/medRxiv preprints (public API) by keyword over a recent date window.",
         {"type": "object", "required": ["query"],
          "properties": {"query": _S,
                         "server": {"type": "string", "enum": ["biorxiv", "medrxiv"], "default": "biorxiv"},
                         "top_k": {"type": "integer", "default": 10},
                         "days_back": {"type": "integer", "default": 180}}},
         _h_search_biorxiv),
]

_BY_NAME: Dict[str, Tool] = {t.name: t for t in TOOLS}


def list_tools() -> List[Dict[str, Any]]:
    """Tool definitions (name, description, input_schema) — no handlers."""
    return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in TOOLS]


def get_tool(name: str) -> Optional[Tool]:
    return _BY_NAME.get(name)


async def call_tool(name: str, args: Dict[str, Any]) -> ToolResult:
    tool = _BY_NAME.get(name)
    if tool is None:
        return ToolResult(False, error=f"Unknown tool: {name}")
    try:
        return await tool.handler(args or {})
    except ValueError as e:
        return ToolResult(False, error=str(e))
    except Exception as e:  # noqa: BLE001
        return ToolResult(False, error=f"{name} failed: {e}")
