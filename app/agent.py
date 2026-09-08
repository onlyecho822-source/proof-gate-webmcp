"""Google ADK entry point for Agentic Cinema.

Gemini orchestrates natural-language work, Parallel supplies fresh web evidence, and
ReleasePathEngine performs the state-dependent routing and deterministic decision math.
"""
from __future__ import annotations

import os
from typing import Any

from .parallel_client import ParallelSearchClient
from .models import ProductionPackage, EvidenceRecord
from .engine import ReleasePathEngine


async def parallel_search_tool(objective: str, search_queries: list[str]) -> dict[str, Any]:
    """Search fresh web evidence with the Parallel Search API."""
    return await ParallelSearchClient().search(objective=objective, search_queries=search_queries)


def evaluate_release_package_tool(
    production_package: dict,
    evidence_records: list[dict],
    case_revision: int = 1,
) -> dict[str, Any]:
    """Run the adaptive router, propagate constraints/worlds, and return a public decision receipt."""
    package = ProductionPackage.model_validate(production_package)
    evidence = [EvidenceRecord.model_validate(x) for x in evidence_records]
    decision = ReleasePathEngine(package, case_revision=case_revision).decide(evidence)
    return decision.model_dump(mode="json")


def release_guardrail_tool(proposed_status: str, evidence_count: int, unresolved_constraints: int) -> dict[str, Any]:
    """Prevent uncertainty from being converted into a legal-clearance claim."""
    proposed = (proposed_status or "").upper()
    if proposed == "GREENLIGHT" and (evidence_count < 1 or unresolved_constraints > 0):
        return {
            "allowed": False,
            "status": "HOLD",
            "reason": "A greenlight cannot be issued while evidence is absent or constraints remain open.",
        }
    return {
        "allowed": True,
        "status": proposed if proposed in {"HOLD", "CONDITIONAL", "GREENLIGHT"} else "HOLD",
        "reason": "Decision-support status accepted; human authority remains required for consequential creative changes.",
    }


try:
    try:
        from google.adk.agents import Agent
    except Exception:
        from google.adk.agents.llm_agent import Agent

    root_agent = Agent(
        name="release_path_router",
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        instruction="""
You are Release Path, a governed media-production decision agent.

The deterministic evaluate_release_package_tool implements a state-dependent cognitive
router. Treat its public mode trace as the authoritative decision structure. Do not
flatten the system back into a generic prompt-answer loop.

Public modes:
- NATE: interpret the practical outcome and test recommendations against it.
- ECHO: map dependencies, blocking bonds, and downstream consequences.
- PROOF: separate assertion from revision-bound evidence.
- OBELISK: attack structural assumptions.
- DEVIL: find the edge case that breaks an apparently correct answer.
- TGC: expand the evidence frame to match territories/distribution scope.
- COUNTERFACTUAL: propose bounded alternate production worlds.
- MINIMUM: find the smallest useful intervention set.
- AUTHORITY: require human permission before consequential creative changes.
- DISTILLATION: expose judge-safe evidence and decision factors, not private prompts.

When current external facts matter, call parallel_search_tool at runtime. Preserve source
URLs/titles/excerpts. Never claim legal clearance, ownership, or license validity.
Use evaluate_release_package_tool for deterministic routing and world comparison.
""",
        tools=[parallel_search_tool, evaluate_release_package_tool, release_guardrail_tool],
    )
except Exception:
    root_agent = None
