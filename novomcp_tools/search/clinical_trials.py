"""ClinicalTrials.gov search via the public API v2 — no key required.

https://clinicaltrials.gov/api/v2/
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

URL = "https://clinicaltrials.gov/api/v2/studies"


async def search_clinical_trials(
    query: Optional[str] = None,
    condition: Optional[str] = None,
    status: str = "ALL",
    phase: str = "ALL",
    top_k: int = 10,
) -> Dict[str, Any]:
    """Search ClinicalTrials.gov. Pass `query` (free text) and/or `condition`.

    `status`: ALL|RECRUITING|ACTIVE_NOT_RECRUITING|COMPLETED|TERMINATED.
    `phase`: ALL|PHASE1|PHASE2|PHASE3|PHASE4. Returns a dict with `trials`.
    """
    if not query and not condition:
        raise ValueError("Missing required parameter: query or condition")
    top_k = min(top_k, 25)

    params: Dict[str, Any] = {"pageSize": top_k, "format": "json", "countTotal": "true"}
    if condition:
        params["query.cond"] = condition
        if query:
            params["query.term"] = query[:200]
    elif query:
        params["query.term"] = query[:200]

    if status != "ALL" and status in {"RECRUITING", "ACTIVE_NOT_RECRUITING", "COMPLETED", "TERMINATED"}:
        params["filter.overallStatus"] = status
    if phase != "ALL" and phase in {"PHASE1", "PHASE2", "PHASE3", "PHASE4"}:
        params["filter.phase"] = phase

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(URL, params=params)
        # v2 API rejects complex queries with 400 — simplify and retry once.
        if response.status_code == 400:
            query_val = params.get("query.term") or params.get("query.cond", "")
            simplified = " ".join(str(query_val).split()[:3])
            response = await client.get(
                URL, params={"pageSize": top_k, "format": "json", "query.term": simplified}
            )
        response.raise_for_status()
        data = response.json()

    trials = []
    for study in data.get("studies", []):
        protocol = study.get("protocolSection", {})
        idm = protocol.get("identificationModule", {})
        statusm = protocol.get("statusModule", {})
        designm = protocol.get("designModule", {})
        descm = protocol.get("descriptionModule", {})
        condm = protocol.get("conditionsModule", {})
        intm = protocol.get("armsInterventionsModule", {})
        sponm = protocol.get("sponsorCollaboratorsModule", {})
        eligm = protocol.get("eligibilityModule", {})
        summary = descm.get("briefSummary", "")
        trials.append(
            {
                "nct_id": idm.get("nctId"),
                "title": idm.get("briefTitle"),
                "status": statusm.get("overallStatus"),
                "phase": ", ".join(designm.get("phases", [])),
                "study_type": designm.get("studyType"),
                "conditions": condm.get("conditions", [])[:5],
                "interventions": [
                    {"type": i.get("type"), "name": i.get("name")}
                    for i in intm.get("interventions", [])[:3]
                ],
                "sponsor": (sponm.get("leadSponsor") or {}).get("name"),
                "enrollment": eligm.get("maximumAge"),
                "start_date": (statusm.get("startDateStruct") or {}).get("date"),
                "completion_date": (statusm.get("completionDateStruct") or {}).get("date"),
                "brief_summary": (summary[:300] + "...") if len(summary) > 300 else summary,
                "url": f"https://clinicaltrials.gov/study/{idm.get('nctId')}",
            }
        )

    out: Dict[str, Any] = {
        "query": query or condition,
        "status_filter": status,
        "phase_filter": phase,
        "total_results": len(trials),
        "total_count": data.get("totalCount", len(trials)),
        "trials": trials,
    }
    if not trials:
        term = condition or query
        out["message"] = (
            f"No clinical trials found for '{term}'. Try a broader term or remove "
            f"status/phase filters. ClinicalTrials.gov uses MeSH terms — e.g. "
            f"'neoplasms' instead of 'cancer'."
        )
    return out
