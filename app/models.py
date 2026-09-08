from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class Mode(str, Enum):
    NATE = "NATE"
    ECHO = "ECHO"
    PROOF = "PROOF"
    OBELISK = "OBELISK"
    DEVIL = "DEVIL"
    TGC = "TGC"
    COUNTERFACTUAL = "COUNTERFACTUAL"
    MINIMUM = "MINIMUM"
    AUTHORITY = "AUTHORITY"
    DISTILLATION = "DISTILLATION"


class Asset(BaseModel):
    id: str
    kind: str
    label: str
    usage_locations: list[str] = Field(default_factory=list)
    territories: list[str] = Field(default_factory=lambda: ["worldwide"])
    search_queries: list[str] = Field(default_factory=list)
    notes: str = ""
    internal_documented: bool = False


class ProductionPackage(BaseModel):
    title: str
    objective: str = "Reach releasable state with minimum disruption"
    release_deadline: str | None = None
    weights: dict[str, float] = Field(default_factory=lambda: {
        "rights_uncertainty": 0.35,
        "cost": 0.20,
        "schedule": 0.20,
        "creative_disruption": 0.20,
        "irreversibility": 0.05,
    })
    assets: list[Asset] = Field(default_factory=list)


class IntentFrame(BaseModel):
    stated_objective: str
    operational_objective: str
    success_condition: str
    non_negotiables: list[str] = Field(default_factory=list)
    target_territories: list[str] = Field(default_factory=list)
    max_delay_hours: float | None = None
    normalized_weights: dict[str, float] = Field(default_factory=dict)


class DependencyEdge(BaseModel):
    source: str
    relation: str
    target: str
    critical: bool = False


class EvidenceRecord(BaseModel):
    id: str
    asset_id: str
    source_label: str
    source_url: str = ""
    excerpt: str
    publish_date: str | None = None
    stance: Literal["supports", "contradicts", "context"] = "context"
    source_family: str = ""
    provenance: str = "parallel"
    reliability: int = Field(default=3, ge=1, le=5)
    claim_revision: int = Field(default=1, ge=1)
    scope_territories: list[str] = Field(default_factory=list)


class Constraint(BaseModel):
    id: str
    asset_id: str
    kind: str
    severity: Literal["low", "medium", "high", "critical"]
    status: Literal["open", "resolved", "unknown"] = "open"
    message: str
    blocks: list[str] = Field(default_factory=list)
    introduced_by: Mode = Mode.PROOF
    claim_revision: int = 1


class ResearchRequest(BaseModel):
    asset_id: str
    reason: str
    territories: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)


class Intervention(BaseModel):
    id: str
    asset_id: str
    action: str
    description: str
    estimated_cost: float = 0.0
    delay_hours: float = 0.0
    creative_disruption: float = Field(default=0.0, ge=0, le=10)
    rights_uncertainty: float = Field(default=0.0, ge=0, le=10)
    irreversibility: float = Field(default=0.0, ge=0, le=10)
    clears_constraints: list[str] = Field(default_factory=list)
    requires_human_approval: bool = True


class World(BaseModel):
    id: str
    label: str
    interventions: list[Intervention]
    cleared_constraints: list[str] = Field(default_factory=list)
    remaining_constraints: list[str]
    affected_edges: int = 0
    metrics: dict[str, float] = Field(default_factory=dict)
    normalized_score: float
    pareto_optimal: bool = False
    status: Literal["blocked", "conditional", "candidate"]
    explanation: str


class ModeEvent(BaseModel):
    seq: int
    mode: Mode
    reason: str
    output_summary: str
    transition_from: Mode | None = None
    state_signal: str = ""


class ReleaseDecision(BaseModel):
    architecture_version: str = "0.3.0"
    project_title: str
    case_revision: int = 1
    current_status: Literal["HOLD", "CONDITIONAL", "GREENLIGHT"]
    intent_frame: IntentFrame | None = None
    dependency_edges: list[DependencyEdge] = Field(default_factory=list)
    all_constraints: list[Constraint] = Field(default_factory=list)
    open_constraints: list[Constraint]
    research_requests: list[ResearchRequest] = Field(default_factory=list)
    worlds: list[World]
    recommended_world_id: str | None = None
    authority_required: bool = False
    mode_trace: list[ModeEvent] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    public_receipt: list[str] = Field(default_factory=list)
    caveat: str = (
        "Decision-support only. This prototype does not make legal determinations "
        "or certify ownership, licensing, or clearance."
    )


class AnalyzeRequest(BaseModel):
    package: ProductionPackage
    live_research: bool = False
    use_gemini_counterfactuals: bool = True
    case_revision: int = Field(default=1, ge=1)


class AuthorityDecision(BaseModel):
    world_id: str
    approved: bool
    note: str = ""


class AuthorityApplyRequest(BaseModel):
    decision_id: str
    world_id: str
    approved: bool
    note: str = ""


class RuntimeStatus(BaseModel):
    app_mode: str
    google_configured: bool
    parallel_configured: bool
    adk_importable: bool
    notes: list[str] = Field(default_factory=list)
