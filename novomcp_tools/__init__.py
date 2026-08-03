"""novomcp-lite — the open-source cheminformatics tool subset of NovoMCP.

Eight zero-config tools (RDKit properties/profiling + public-API search),
usable as a library or over MCP. Apache-2.0. No orchestration core, no
services, no keys.

    from novomcp_tools import compute_properties, molecule_profile
    from novomcp_tools import call_tool, list_tools          # tool surface
    from novomcp_tools.search import search_chembl           # async
"""
from .chem import compute_properties, compute_sa_score, molecule_profile, structural_alerts
from .registry import TOOLS, ToolResult, call_tool, get_tool, list_tools

__version__ = "0.1.1"

__all__ = [
    "__version__",
    "compute_properties",
    "compute_sa_score",
    "structural_alerts",
    "molecule_profile",
    "TOOLS",
    "ToolResult",
    "call_tool",
    "get_tool",
    "list_tools",
]
