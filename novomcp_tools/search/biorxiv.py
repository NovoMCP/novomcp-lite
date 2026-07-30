"""bioRxiv / medRxiv preprint search via the public API — no key required.

https://api.biorxiv.org/

The /details endpoint returns papers in 100-item pages by date, not by query,
so we fetch a page, filter in-memory, and fall back to a shorter window on
timeout.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

import httpx


async def _fetch(server: str, window_days: int, timeout_s: float) -> List[dict]:
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d")
    api_url = f"https://api.biorxiv.org/details/{server}/{start_date}/{end_date}/0/100"
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        response = await client.get(api_url)
        response.raise_for_status()
        return response.json().get("collection", [])


async def search_biorxiv(
    query: str, server: str = "biorxiv", top_k: int = 10, days_back: int = 180
) -> Dict[str, Any]:
    """Search bioRxiv/medRxiv preprints. `server`: "biorxiv" | "medrxiv".

    Matches papers whose title/abstract contain any query term. Returns a dict
    with `preprints`.
    """
    if not query:
        raise ValueError("Missing required parameter: query")
    top_k = min(top_k, 30)

    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    try:
        collection = await _fetch(server, days_back, 60.0)
    except (httpx.TimeoutException, httpx.ReadTimeout):
        try:
            collection = await _fetch(server, 60, 30.0)
            start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        except (httpx.TimeoutException, httpx.ReadTimeout):
            collection = []

    terms = [t.strip().lower() for t in query.split() if len(t.strip()) >= 3] or [query.lower()]
    matches = []
    for paper in collection:
        title = (paper.get("title") or "").lower()
        abstract = (paper.get("abstract") or "").lower()
        if any(term in title or term in abstract for term in terms):
            raw_abs = paper.get("abstract", "") or ""
            matches.append(
                {
                    "doi": paper.get("doi"),
                    "title": paper.get("title"),
                    "abstract": (raw_abs[:500] + "...") if len(raw_abs) > 500 else raw_abs,
                    "authors": paper.get("authors"),
                    "date": paper.get("date"),
                    "category": paper.get("category"),
                    "server": server,
                    "url": f"https://www.{server}.org/content/{paper.get('doi')}",
                }
            )
            if len(matches) >= top_k:
                break

    return {
        "query": query,
        "server": server,
        "date_range": f"{start_date} to {end_date}",
        "total_results": len(matches),
        "preprints": matches,
    }
