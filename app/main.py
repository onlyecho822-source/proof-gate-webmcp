from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .agent import root_agent
from .demo_data import sample_package, sample_evidence
from .engine import ReleasePathEngine, apply_authorized_world
from .evidence import normalize_parallel_results
from .gemini import generate_interventions_with_gemini, google_configured, GeminiRuntimeError
from .models import (
    AnalyzeRequest,
    AuthorityApplyRequest,
    EvidenceRecord,
    Intervention,
    ProductionPackage,
    ReleaseDecision,
    RuntimeStatus,
)
from .parallel_client import ParallelSearchClient, ParallelSearchError

APP_VERSION = "0.3.1-external"
HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"

app = FastAPI(
    title="Release Path",
    version=APP_VERSION,
    description="Governed media-production decision support for Agentic Cinema.",
)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

# Server-issued snapshots make AUTHORITY operate on an actual prior decision, not on a
# client-fabricated world. This is intentionally in-memory for the hackathon prototype.
DECISION_STORE: dict[str, dict[str, Any]] = {}


def _store(package: ProductionPackage, evidence: list[EvidenceRecord], decision: ReleaseDecision) -> str:
    decision_id = f"decision-{uuid.uuid4().hex[:16]}"
    DECISION_STORE[decision_id] = {
        "package": package.model_copy(deep=True),
        "evidence": [e.model_copy(deep=True) for e in evidence],
        "decision": decision.model_copy(deep=True),
    }
    # bounded demo store
    if len(DECISION_STORE) > 100:
        for key in list(DECISION_STORE)[:-100]:
            DECISION_STORE.pop(key, None)
    return decision_id


def _json_response(decision_id: str, package: ProductionPackage, decision: ReleaseDecision) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "package": package.model_dump(mode="json"),
        "decision": decision.model_dump(mode="json"),
    }


def _parallel_client() -> ParallelSearchClient:
    return ParallelSearchClient()


async def _research_asset(
    client: ParallelSearchClient,
    package: ProductionPackage,
    asset_id: str,
    queries: list[str],
    *,
    case_revision: int,
    provenance: str,
) -> list[EvidenceRecord]:
    asset = next((a for a in package.assets if a.id == asset_id), None)
    if not asset:
        return []
    payload = await client.search(
        objective=(
            f"Find fresh, traceable public information relevant to rights/permission evidence for "
            f"the media-production asset '{asset.label}'. Do not infer legal clearance."
        ),
        search_queries=queries or asset.search_queries or [asset.label],
        max_results=6,
    )
    return normalize_parallel_results(
        asset.id,
        payload,
        claim_revision=case_revision,
        target_territories=asset.territories,
        provenance=provenance,
    )


async def _live_decide(request: AnalyzeRequest) -> tuple[ProductionPackage, list[EvidenceRecord], ReleaseDecision]:
    package = request.package
    revision = request.case_revision
    evidence: list[EvidenceRecord] = []
    client = _parallel_client()

    if request.live_research:
        if not client.configured:
            raise HTTPException(status_code=503, detail="Live mode requires PARALLEL_API_KEY")
        for asset in package.assets:
            try:
                evidence.extend(await _research_asset(
                    client, package, asset.id, asset.search_queries,
                    case_revision=revision, provenance="parallel-search",
                ))
            except ParallelSearchError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc

    # First pass exposes the state-dependent proof frame and any TGC research expansion.
    decision = ReleasePathEngine(package, case_revision=revision).decide(evidence)

    # TGC can widen the evidence frame, then PROOF is run again with the added evidence.
    if request.live_research and decision.research_requests:
        for rr in decision.research_requests[:6]:
            try:
                evidence.extend(await _research_asset(
                    client, package, rr.asset_id, rr.search_queries,
                    case_revision=revision, provenance="parallel-search-tgc",
                ))
            except ParallelSearchError as exc:
                raise HTTPException(status_code=502, detail=str(exc)) from exc
        decision = ReleasePathEngine(package, case_revision=revision).decide(evidence)

    external_interventions: list[Intervention] | None = None
    if request.use_gemini_counterfactuals:
        if not google_configured():
            if request.live_research:
                raise HTTPException(status_code=503, detail="Competition live mode requires GOOGLE_CLOUD_PROJECT for Gemini/Vertex AI")
        else:
            context = {
                "production": package.model_dump(mode="json"),
                "case_revision": revision,
                "open_constraints": [c.model_dump(mode="json") for c in decision.open_constraints],
                "dependency_edges": [e.model_dump(mode="json") for e in decision.dependency_edges],
                "evidence": [e.model_dump(mode="json") for e in evidence],
            }
            try:
                raw = await generate_interventions_with_gemini(context)
                candidates: list[Intervention] = []
                for idx, row in enumerate(raw, 1):
                    if not isinstance(row, dict):
                        continue
                    row = dict(row)
                    row.setdefault("id", f"gemini-{idx}")
                    row["requires_human_approval"] = True
                    try:
                        candidates.append(Intervention.model_validate(row))
                    except Exception:
                        continue
                external_interventions = candidates or None
            except GeminiRuntimeError as exc:
                if request.live_research:
                    raise HTTPException(status_code=502, detail=str(exc)) from exc

    if external_interventions:
        decision = ReleasePathEngine(package, case_revision=revision).decide(
            evidence, external_interventions=external_interventions
        )
    return package, evidence, decision


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {"ok": True, "version": APP_VERSION}


@app.get("/api/runtime", response_model=RuntimeStatus)
def runtime_status() -> RuntimeStatus:
    parallel = _parallel_client()
    g = google_configured()
    adk = root_agent is not None
    notes: list[str] = []
    if not parallel.configured:
        notes.append("PARALLEL_API_KEY is not configured; deterministic demo remains available.")
    if not g:
        notes.append("GOOGLE_CLOUD_PROJECT is not configured; Gemini live counterfactuals are unavailable.")
    if not adk:
        notes.append("Google ADK root agent is not importable in this runtime.")
    return RuntimeStatus(
        app_mode=os.getenv("APP_MODE", "competition"),
        google_configured=g,
        parallel_configured=parallel.configured,
        adk_importable=adk,
        notes=notes,
    )


@app.get("/api/demo")
def demo() -> dict[str, Any]:
    package = sample_package()
    evidence = sample_evidence()
    decision = ReleasePathEngine(package, case_revision=1).decide(evidence)
    decision_id = _store(package, evidence, decision)
    return _json_response(decision_id, package, decision)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, Any]:
    package, evidence, decision = await _live_decide(request)
    decision_id = _store(package, evidence, decision)
    response = _json_response(decision_id, package, decision)
    response["runtime"] = runtime_status().model_dump(mode="json")
    return response


@app.post("/api/authority")
async def authority(request: AuthorityApplyRequest) -> dict[str, Any]:
    snapshot = DECISION_STORE.get(request.decision_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Decision snapshot not found or expired")
    prior: ReleaseDecision = snapshot["decision"]
    package: ProductionPackage = snapshot["package"]
    evidence: list[EvidenceRecord] = snapshot["evidence"]
    world = next((w for w in prior.worlds if w.id == request.world_id), None)
    if not world or request.world_id != prior.recommended_world_id:
        raise HTTPException(status_code=400, detail="Authority can only act on the server-issued recommended world")
    if not request.approved:
        return {
            "approved": False,
            "decision_id": request.decision_id,
            "case_revision": prior.case_revision,
            "status": "HOLD",
            "note": request.note,
            "message": "Producer declined the proposed mutation; production state was not changed.",
        }

    next_revision = prior.case_revision + 1
    revised_package, historical_evidence, changes = apply_authorized_world(
        package, evidence, world, case_revision=prior.case_revision
    )

    # Authority never turns old evidence into new evidence. Live mode, when configured,
    # re-researches the changed revision; otherwise PROOF fails closed on the new revision.
    fresh: list[EvidenceRecord] = []
    client = _parallel_client()
    if client.configured:
        for asset in revised_package.assets:
            try:
                fresh.extend(await _research_asset(
                    client, revised_package, asset.id, asset.search_queries,
                    case_revision=next_revision, provenance="parallel-search-after-authority",
                ))
            except ParallelSearchError:
                # Fail closed: do not manufacture evidence if the live partner call fails.
                fresh = []
                break

    revised_evidence = historical_evidence + fresh
    revised_decision = ReleasePathEngine(revised_package, case_revision=next_revision).decide(revised_evidence)
    new_id = _store(revised_package, revised_evidence, revised_decision)
    return {
        "approved": True,
        "previous_decision_id": request.decision_id,
        "decision_id": new_id,
        "changes": changes,
        "package": revised_package.model_dump(mode="json"),
        "decision": revised_decision.model_dump(mode="json"),
        "message": "Human authority created a new production revision. PROOF was rerun; old evidence remained historical only.",
    }
