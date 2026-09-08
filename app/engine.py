from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import product
from math import inf
from typing import Iterable

from .models import (
    Mode,
    Asset,
    ProductionPackage,
    IntentFrame,
    DependencyEdge,
    EvidenceRecord,
    Constraint,
    ResearchRequest,
    Intervention,
    World,
    ModeEvent,
    ReleaseDecision,
)
from .evidence import evaluate_evidence, build_tgc_research_requests


BLOCKING_KINDS = {
    "evidence-gap",
    "direct-contradiction",
    "source-concentration",
    "future-date",
    "stale-evidence",
    "unknown-date",
    "internal-documentation",
    "cross-deliverable-dependency",
    "territory-split",
    "evidence-frame-insufficient",
}


@dataclass
class RouterState:
    intent_frame: IntentFrame | None = None
    dependency_edges: list[DependencyEdge] = field(default_factory=list)
    graph_dirty: bool = False
    proof_verified: bool = False
    obelisk_done: bool = False
    devil_done: bool = False
    tgc_done: bool = False
    research_requests: list[ResearchRequest] = field(default_factory=list)
    external_candidates: list[Intervention] | None = None
    interventions: list[Intervention] | None = None
    worlds: list[World] = field(default_factory=list)
    recommended_world_id: str | None = None
    recommendation_checked: bool = False
    authority_required: bool = False
    distilled: bool = False
    final_status: str | None = None
    halt_reason: str = ""
    all_constraints: list[Constraint] = field(default_factory=list)
    trace: list[ModeEvent] = field(default_factory=list)
    visits: dict[Mode, int] = field(default_factory=lambda: defaultdict(int))


class ReleasePathEngine:
    def __init__(self, package: ProductionPackage, *, case_revision: int = 1, now: datetime | None = None):
        self.package = package
        self.case_revision = case_revision
        self.now = now or datetime.now(timezone.utc)
        self.assets = {asset.id: asset for asset in package.assets}

    def _event(self, state: RouterState, mode: Mode, reason: str, summary: str, signal: str = "") -> None:
        state.visits[mode] += 1
        state.trace.append(ModeEvent(
            seq=len(state.trace) + 1,
            mode=mode,
            reason=reason,
            output_summary=summary,
            transition_from=state.trace[-1].mode if state.trace else None,
            state_signal=signal,
        ))

    def _upsert_constraint(self, state: RouterState, item: Constraint) -> bool:
        for idx, existing in enumerate(state.all_constraints):
            if existing.id == item.id:
                state.all_constraints[idx] = item
                return False
        state.all_constraints.append(item)
        return True

    def _open_constraints(self, state: RouterState) -> list[Constraint]:
        return [c for c in state.all_constraints if c.status in {"open", "unknown"} and c.kind in BLOCKING_KINDS]

    def _remaining_hours(self) -> float | None:
        if not self.package.release_deadline:
            return None
        try:
            deadline = datetime.fromisoformat(self.package.release_deadline.replace("Z", "+00:00"))
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return max(0.0, (deadline - self.now).total_seconds() / 3600)
        except ValueError:
            return None

    def _build_intent_frame(self) -> IntentFrame:
        targets = sorted({territory for asset in self.package.assets for territory in asset.territories})
        raw = {k: max(0.0, float(v)) for k, v in self.package.weights.items()}
        total = sum(raw.values()) or 1.0
        weights = {k: v / total for k, v in raw.items()}
        remaining = self._remaining_hours()
        non_negotiables = ["Do not represent missing evidence as legal clearance", "Preserve human authority over creative mutation"]
        if remaining is not None:
            non_negotiables.append(f"Meet the declared release deadline with no more than {round(remaining, 1)} hours available")
        return IntentFrame(
            stated_objective=self.package.objective,
            operational_objective=(
                "Reach a decision-support state compatible with the declared release deadline while minimizing "
                "creative disruption, cost, schedule delay, rights uncertainty, irreversibility, and graph disturbance."
            ),
            success_condition=(
                "No active blocker is hidden, the recommended production world has no unresolved release blockers, "
                "and any consequential change remains behind human authority before re-verification."
            ),
            non_negotiables=non_negotiables,
            target_territories=targets,
            max_delay_hours=remaining,
            normalized_weights=weights,
        )

    def _build_dependency_graph(self, state: RouterState) -> list[DependencyEdge]:
        edges: list[DependencyEdge] = []
        for asset in self.package.assets:
            for usage in asset.usage_locations:
                edges.append(DependencyEdge(source=asset.id, relation="used_in", target=usage, critical=True))
                edges.append(DependencyEdge(source=usage, relation="depends_on_rights_evidence_for", target=asset.id, critical=True))
            for territory in asset.territories:
                edges.append(DependencyEdge(source=asset.id, relation="distributed_in", target=territory, critical=True))
            for query in asset.search_queries[:2]:
                edges.append(DependencyEdge(source=asset.id, relation="evidence_query", target=query, critical=False))

        # Adversarial findings become first-class graph edges. This is how ECHO is
        # legitimately re-entered instead of being a decorative second pass.
        for c in state.all_constraints:
            if c.status not in {"open", "unknown"}:
                continue
            if c.kind == "cross-deliverable-dependency":
                edges.append(DependencyEdge(source=c.asset_id, relation="couples_deliverables", target=" + ".join(c.blocks), critical=True))
            elif c.kind == "territory-split":
                edges.append(DependencyEdge(source=c.asset_id, relation="requires_per_territory_proof", target=" + ".join(c.blocks), critical=True))
            elif c.kind == "evidence-frame-insufficient":
                edges.append(DependencyEdge(source=c.asset_id, relation="missing_evidence_scope", target=" + ".join(c.blocks), critical=True))
        # deterministic de-dupe
        seen = set()
        unique: list[DependencyEdge] = []
        for edge in edges:
            key = (edge.source, edge.relation, edge.target, edge.critical)
            if key not in seen:
                seen.add(key)
                unique.append(edge)
        return unique

    def _run_proof(self, state: RouterState, evidence: list[EvidenceRecord]) -> None:
        # PROOF results are recomputed from revision-bound evidence, while structural
        # OBELISK/DEVIL/TGC findings remain unless later production mutation clears them.
        state.all_constraints = [
            c for c in state.all_constraints
            if c.introduced_by in {Mode.OBELISK, Mode.DEVIL, Mode.TGC}
        ]
        for asset in self.package.assets:
            for item in evaluate_evidence(asset, evidence, claim_revision=self.case_revision, now=self.now):
                self._upsert_constraint(state, item)
        state.proof_verified = True

    def _run_obelisk(self, state: RouterState) -> int:
        added = 0
        for asset in self.package.assets:
            if len(asset.usage_locations) > 1:
                item = Constraint(
                    id=f"{asset.id}:cross-deliverable:r{self.case_revision}", asset_id=asset.id,
                    kind="cross-deliverable-dependency", severity="high",
                    message=(
                        f"{asset.label} appears in multiple deliverables ({', '.join(asset.usage_locations)}). "
                        "A fix in one cut must not be assumed to clear the others."
                    ),
                    blocks=asset.usage_locations, introduced_by=Mode.OBELISK, claim_revision=self.case_revision,
                )
                if self._upsert_constraint(state, item):
                    added += 1
        state.obelisk_done = True
        return added

    def _run_devil(self, state: RouterState) -> int:
        added = 0
        for asset in self.package.assets:
            if len({t.lower() for t in asset.territories}) > 1 and not any(t.lower() == "worldwide" for t in asset.territories):
                item = Constraint(
                    id=f"{asset.id}:territory-split:r{self.case_revision}", asset_id=asset.id,
                    kind="territory-split", severity="high",
                    message=(
                        f"The asset spans {', '.join(asset.territories)}. Evidence supporting one territory cannot "
                        "silently establish another."
                    ),
                    blocks=asset.territories, introduced_by=Mode.DEVIL, claim_revision=self.case_revision,
                )
                if self._upsert_constraint(state, item):
                    added += 1
        state.devil_done = True
        return added

    def _run_tgc(self, state: RouterState, evidence: list[EvidenceRecord]) -> int:
        requests = build_tgc_research_requests(self.package.assets, evidence, claim_revision=self.case_revision)
        state.research_requests = requests
        added = 0
        for req in requests:
            item = Constraint(
                id=f"{req.asset_id}:evidence-frame:r{self.case_revision}", asset_id=req.asset_id,
                kind="evidence-frame-insufficient", severity="high",
                message=f"Evidence frame does not explicitly cover intended distribution scope: {', '.join(req.territories)}.",
                blocks=req.territories, introduced_by=Mode.TGC, claim_revision=self.case_revision,
            )
            if self._upsert_constraint(state, item):
                added += 1
        state.tgc_done = True
        return added

    def _candidate_actions(self, asset: Asset, constraints: list[Constraint]) -> list[Intervention]:
        ids = [c.id for c in constraints]
        return [
            Intervention(
                id=f"{asset.id}:verify", asset_id=asset.id, action="verify/secure evidence",
                description=f"Obtain authoritative, territory-appropriate permission or license evidence for {asset.label}.",
                estimated_cost=350, delay_hours=72, creative_disruption=0.5, rights_uncertainty=2,
                irreversibility=1, clears_constraints=ids, requires_human_approval=True,
            ),
            Intervention(
                id=f"{asset.id}:replace", asset_id=asset.id, action="replace asset",
                description=f"Replace {asset.label} with an asset carrying clearer rights evidence for the intended scope.",
                estimated_cost=1200, delay_hours=8, creative_disruption=5, rights_uncertainty=1,
                irreversibility=3, clears_constraints=ids, requires_human_approval=True,
            ),
            Intervention(
                id=f"{asset.id}:remove", asset_id=asset.id, action="remove usage",
                description=f"Remove {asset.label} from every coupled usage in this release package.",
                estimated_cost=250, delay_hours=4, creative_disruption=7, rights_uncertainty=0,
                irreversibility=2, clears_constraints=ids, requires_human_approval=True,
            ),
        ]

    def _sanitize_external_candidates(
        self,
        candidates: list[Intervention],
        blocked_by_asset: dict[str, list[Constraint]],
    ) -> list[Intervention]:
        valid_constraint_ids = {c.id for rows in blocked_by_asset.values() for c in rows}
        sanitized: list[Intervention] = []
        for idx, candidate in enumerate(candidates[:12], 1):
            if candidate.asset_id not in blocked_by_asset:
                continue
            clears = [cid for cid in candidate.clears_constraints if cid in valid_constraint_ids]
            if not clears:
                continue
            sanitized.append(candidate.model_copy(update={
                "id": candidate.id or f"external-{idx}",
                "clears_constraints": clears,
                "requires_human_approval": True,
            }))
        return sanitized

    def _generate_interventions(
        self,
        state: RouterState,
    ) -> list[Intervention]:
        blocked_by_asset: dict[str, list[Constraint]] = defaultdict(list)
        for c in self._open_constraints(state):
            if c.asset_id in self.assets:
                blocked_by_asset[c.asset_id].append(c)

        external = self._sanitize_external_candidates(state.external_candidates or [], blocked_by_asset)
        external_by_asset = {c.asset_id for c in external}
        deterministic: list[Intervention] = []
        for asset_id, constraints in blocked_by_asset.items():
            if asset_id not in external_by_asset:
                deterministic.extend(self._candidate_actions(self.assets[asset_id], constraints))
        return (external + deterministic)[:18]

    def _affected_edge_count(self, interventions: Iterable[Intervention], edges: list[DependencyEdge]) -> int:
        changed = {i.asset_id for i in interventions}
        return sum(1 for edge in edges if edge.source in changed or edge.target in changed)

    def _world_metrics(self, combo: Iterable[Intervention], edges: list[DependencyEdge]) -> dict[str, float]:
        items = list(combo)
        return {
            "estimated_cost": sum(i.estimated_cost for i in items),
            "delay_hours": max((i.delay_hours for i in items), default=0.0),
            "creative_disruption": sum(i.creative_disruption for i in items) / max(1, len(items)),
            "rights_uncertainty": sum(i.rights_uncertainty for i in items) / max(1, len(items)),
            "irreversibility": sum(i.irreversibility for i in items) / max(1, len(items)),
            "intervention_count": float(len(items)),
            "affected_edges": float(self._affected_edge_count(items, edges)),
        }

    def _weighted_score(self, metrics: dict[str, float], intent: IntentFrame) -> float:
        # A bounded scalar is retained only as a late tie-breaker / explanation.
        cost_n = min(1.0, metrics["estimated_cost"] / 10000)
        delay_n = min(1.0, metrics["delay_hours"] / (max(1.0, intent.max_delay_hours or 168.0)))
        disruption_n = metrics["creative_disruption"] / 10
        rights_n = metrics["rights_uncertainty"] / 10
        irreversibility_n = metrics["irreversibility"] / 10
        values = {
            "cost": cost_n, "schedule": delay_n, "creative_disruption": disruption_n,
            "rights_uncertainty": rights_n, "irreversibility": irreversibility_n,
        }
        return round(sum(intent.normalized_weights.get(k, 0) * values.get(k, 0) for k in intent.normalized_weights), 4)

    def _dominates(self, a: World, b: World) -> bool:
        keys = (
            "estimated_cost", "delay_hours", "creative_disruption", "rights_uncertainty",
            "irreversibility", "intervention_count", "affected_edges",
        )
        return all(a.metrics[k] <= b.metrics[k] for k in keys) and any(a.metrics[k] < b.metrics[k] for k in keys)

    def _build_worlds(self, state: RouterState) -> list[World]:
        constraints = self._open_constraints(state)
        if not constraints or not state.interventions:
            return []
        by_asset: dict[str, list[Intervention]] = defaultdict(list)
        for intervention in state.interventions:
            by_asset[intervention.asset_id].append(intervention)
        assets = sorted(by_asset)
        if not assets:
            return []
        combos = list(product(*(by_asset[asset][:3] for asset in assets)))[:12]
        all_ids = {c.id for c in constraints}
        worlds: list[World] = []
        for idx, combo in enumerate(combos, 1):
            cleared = {cid for i in combo for cid in i.clears_constraints}
            remaining = sorted(all_ids - cleared)
            metrics = self._world_metrics(combo, state.dependency_edges)
            score = self._weighted_score(metrics, state.intent_frame or self._build_intent_frame())
            worlds.append(World(
                id=f"world-{idx:02d}", label=" + ".join(i.action for i in combo), interventions=list(combo),
                cleared_constraints=sorted(cleared), remaining_constraints=remaining,
                affected_edges=int(metrics["affected_edges"]), metrics=metrics,
                normalized_score=score, status="candidate" if remaining else "conditional",
                explanation=(
                    f"Changes {int(metrics['intervention_count'])} asset decision(s), touches {int(metrics['affected_edges'])} dependency edges, "
                    f"costs about ${metrics['estimated_cost']:.0f}, and delays up to {metrics['delay_hours']:.0f}h."
                ),
            ))
        for world in worlds:
            world.pareto_optimal = not any(other.id != world.id and self._dominates(other, world) for other in worlds)
        return worlds

    def _minimum_useful_world(self, state: RouterState) -> World | None:
        viable = [w for w in state.worlds if not w.remaining_constraints]
        if not viable:
            return None
        pareto = [w for w in viable if w.pareto_optimal] or viable

        def key(w: World):
            # MUA principle: first minimize number of interventions and graph disturbance,
            # then rights uncertainty/reversibility; only then use the configured weighted score.
            return (
                w.metrics["intervention_count"],
                w.metrics["affected_edges"],
                w.metrics["rights_uncertainty"],
                w.metrics["irreversibility"],
                w.normalized_score,
                w.metrics["delay_hours"],
                w.metrics["estimated_cost"],
                w.id,
            )

        return min(pareto, key=key)

    def _deadline_feasible_alternative(self, state: RouterState) -> World | None:
        intent = state.intent_frame
        if not intent or intent.max_delay_hours is None:
            return None
        viable = [w for w in state.worlds if not w.remaining_constraints and w.metrics["delay_hours"] <= intent.max_delay_hours]
        if not viable:
            return None
        return min(viable, key=lambda w: (
            w.metrics["intervention_count"], w.metrics["affected_edges"],
            w.metrics["rights_uncertainty"], w.metrics["creative_disruption"],
            w.normalized_score, w.id,
        ))

    def _public_receipt(self, state: RouterState) -> list[str]:
        open_items = self._open_constraints(state)
        receipt = [
            f"Production revision {self.case_revision}; status {state.final_status or 'HOLD'}.",
            f"State-dependent router executed {len(state.trace)} mode transitions; modes may repeat or be skipped when state changes.",
            f"{len(open_items)} open blocker(s) remain after revision-bound evidence and adversarial review.",
        ]
        if state.research_requests:
            scope = sorted({t for r in state.research_requests for t in r.territories})
            receipt.append(f"TGC found the evidence frame incomplete for: {', '.join(scope)}.")
        if state.recommended_world_id:
            receipt.append(f"Minimum useful candidate: {state.recommended_world_id}; human authority required before mutation.")
        else:
            receipt.append("No production mutation is authorized by this receipt.")
        receipt.append("External research remains evidence input, not automatic legal truth; private prompts are not exposed in this receipt.")
        return receipt

    def _next_mode(self, state: RouterState) -> Mode | None:
        if state.intent_frame is None:
            return Mode.NATE
        if not state.dependency_edges or state.graph_dirty:
            return Mode.ECHO
        if not state.proof_verified:
            return Mode.PROOF
        if not state.obelisk_done:
            return Mode.OBELISK
        if state.graph_dirty:
            return Mode.ECHO
        if not state.devil_done:
            return Mode.DEVIL
        if state.graph_dirty:
            return Mode.ECHO
        if not state.tgc_done:
            return Mode.TGC
        if state.graph_dirty:
            return Mode.ECHO
        # TGC may reveal that the distribution evidence frame is too narrow. PROOF is
        # re-entered to make that new evidence-frame state part of the active proof view.
        if state.research_requests and state.visits[Mode.PROOF] < 2:
            return Mode.PROOF
        if state.visits[Mode.PROOF] >= 2 and state.research_requests:
            # This local pass cannot invent the missing external evidence. It acknowledges
            # the expanded proof frame and continues to counterfactual planning.
            state.proof_verified = True
        if self._open_constraints(state):
            if state.interventions is None:
                return Mode.COUNTERFACTUAL
            if not state.worlds:
                return Mode.ECHO
            if state.recommended_world_id is None:
                return Mode.MINIMUM
            if not state.recommendation_checked:
                return Mode.NATE
            if state.authority_required:
                return Mode.AUTHORITY
        if state.final_status is None:
            state.final_status = "GREENLIGHT" if not self._open_constraints(state) else "HOLD"
        if not state.distilled:
            return Mode.DISTILLATION
        return None

    def decide(
        self,
        evidence: list[EvidenceRecord],
        external_interventions: list[Intervention] | None = None,
    ) -> ReleaseDecision:
        state = RouterState(external_candidates=external_interventions)
        previous: Mode | None = None
        for _ in range(36):
            mode = self._next_mode(state)
            if mode is None:
                break
            if state.visits[mode] >= 5:
                state.final_status = "HOLD"
                state.halt_reason = f"Router loop guard stopped repeated {mode.value} execution."
                if not state.distilled:
                    mode = Mode.DISTILLATION
                else:
                    break

            if mode == Mode.NATE:
                if state.intent_frame is None:
                    state.intent_frame = self._build_intent_frame()
                    self._event(state, mode, "The raw question is not yet an operational objective.",
                                f"Framed outcome with {len(state.intent_frame.target_territories)} target territory/territories and an explicit deadline budget.",
                                "objective-framed")
                else:
                    candidate = next((w for w in state.worlds if w.id == state.recommended_world_id), None)
                    if candidate and state.intent_frame.max_delay_hours is not None and candidate.metrics["delay_hours"] > state.intent_frame.max_delay_hours:
                        alternate = self._deadline_feasible_alternative(state)
                        if alternate:
                            prior = state.recommended_world_id
                            state.recommended_world_id = alternate.id
                            state.recommendation_checked = True
                            state.authority_required = any(i.requires_human_approval for i in alternate.interventions)
                            self._event(state, mode, "The mathematical minimum must still satisfy the producer's real deadline.",
                                        f"Rejected {prior} because it needs {candidate.metrics['delay_hours']:.0f}h; reframed to deadline-feasible {alternate.id}.",
                                        "objective-reframed-after-counterfactual")
                        else:
                            state.recommendation_checked = True
                            state.recommended_world_id = None
                            state.authority_required = False
                            state.final_status = "HOLD"
                            state.halt_reason = "No counterfactual world clears the blockers within the declared deadline."
                            self._event(state, mode, "No candidate world satisfies the actual objective.",
                                        state.halt_reason, "recommended-world-misses-objective")
                    else:
                        state.recommendation_checked = True
                        state.authority_required = bool(candidate and any(i.requires_human_approval for i in candidate.interventions))
                        self._event(state, mode, "The selected minimum must be checked against the operational objective.",
                                    "Recommendation remains compatible with the declared deadline and producer constraints.",
                                    "recommendation-reality-checked")

            elif mode == Mode.ECHO:
                if not state.worlds and state.interventions is not None:
                    state.worlds = self._build_worlds(state)
                    self._event(state, mode, "Candidate interventions exist but their downstream worlds are not mapped.",
                                f"Propagated {len(state.worlds)} alternate production worlds through {len(state.dependency_edges)} current dependency edges.",
                                "counterfactual-worlds-propagated")
                else:
                    state.dependency_edges = self._build_dependency_graph(state)
                    state.graph_dirty = False
                    self._event(state, mode, "Relationships or newly discovered blocking bonds need mapping.",
                                f"Mapped {len(state.dependency_edges)} dependency edges including adversarially discovered bonds.",
                                "dependency-graph-built" if state.visits[Mode.ECHO] == 1 else "dependency-graph-rebuilt")

            elif mode == Mode.PROOF:
                self._run_proof(state, evidence)
                self._event(state, mode, "The current claim revision requires an evidence gate.",
                            f"Bound evidence to production revision {self.case_revision}; {len(self._open_constraints(state))} blocker(s) remain.",
                            "evidence-verified" if state.visits[Mode.PROOF] == 1 else "evidence-reverified-after-frame-change")

            elif mode == Mode.OBELISK:
                added = self._run_obelisk(state)
                state.graph_dirty = added > 0
                self._event(state, mode, "The current answer must be attacked structurally before planning action.",
                            f"Found {added} new structural coupling risk(s)." if added else "No new structural coupling risk was added.",
                            "new-blocking-bond" if added else "no-new-bond")

            elif mode == Mode.DEVIL:
                added = self._run_devil(state)
                state.graph_dirty = added > 0
                self._event(state, mode, "Failure is costly; test the edge case that could invalidate an apparently correct answer.",
                            f"Found {added} territory/edge-case risk(s)." if added else "No additional edge-case blocker was added.",
                            "edge-case-changed-graph" if added else "edge-case-clean")

            elif mode == Mode.TGC:
                added = self._run_tgc(state, evidence)
                state.graph_dirty = added > 0
                if state.research_requests:
                    state.proof_verified = False
                self._event(state, mode, "Local evidence must match the intended global/distribution frame.",
                            f"Expanded evidence requirements for {len(state.research_requests)} asset(s); {added} frame-gap blocker(s) added.",
                            "evidence-frame-expanded" if added else "evidence-frame-sufficient")

            elif mode == Mode.COUNTERFACTUAL:
                state.interventions = self._generate_interventions(state)
                source = "Gemini-generated candidates" if state.external_candidates else "deterministic fallback candidates"
                self._event(state, mode, "Open blockers exist and alternate feasible production states are needed.",
                            f"Generated {len(state.interventions)} bounded intervention candidates using {source}; decision scoring remains deterministic.",
                            "alternate-actions-generated")

            elif mode == Mode.MINIMUM:
                selected = self._minimum_useful_world(state)
                if selected:
                    state.recommended_world_id = selected.id
                    self._event(state, mode, "Viable worlds exist; collapse to a Pareto-minimal intervention set before using scalar preference.",
                                f"Selected {selected.id}: {int(selected.metrics['intervention_count'])} intervention(s), {int(selected.metrics['affected_edges'])} affected edge(s), weighted tie-break {selected.normalized_score:.3f}.",
                                "minimum-useful-action-selected")
                else:
                    state.final_status = "HOLD"
                    state.halt_reason = "No generated world clears every active blocker."
                    self._event(state, mode, "No feasible clearing world exists.", state.halt_reason, "no-viable-world")

            elif mode == Mode.AUTHORITY:
                state.final_status = "CONDITIONAL"
                self._event(state, mode, "The recommended path changes creative/production state and capability is not authority.",
                            f"Stopped before applying {state.recommended_world_id}; producer approval is required and will create a new revision requiring PROOF again.",
                            "human-authority-required")
                state.authority_required = False

            elif mode == Mode.DISTILLATION:
                state.distilled = True
                self._event(state, mode, "External judges need decision factors without private prompt material.",
                            "Produced a public receipt containing mode transitions, evidence state, blockers, recommendation, and authority boundary.",
                            "public-receipt-ready")
            previous = mode
        else:
            state.final_status = "HOLD"
            state.halt_reason = "Router iteration limit reached."

        if state.final_status is None:
            state.final_status = "GREENLIGHT" if not self._open_constraints(state) else "HOLD"
        receipt = self._public_receipt(state)
        return ReleaseDecision(
            project_title=self.package.title,
            case_revision=self.case_revision,
            current_status=state.final_status,
            intent_frame=state.intent_frame,
            dependency_edges=state.dependency_edges,
            all_constraints=state.all_constraints,
            open_constraints=self._open_constraints(state),
            research_requests=state.research_requests,
            worlds=state.worlds,
            recommended_world_id=state.recommended_world_id,
            authority_required=(state.final_status == "CONDITIONAL" and state.recommended_world_id is not None),
            mode_trace=state.trace,
            evidence=evidence,
            public_receipt=receipt,
            caveat=(
                "Decision-support only. No legal clearance is certified. " + (state.halt_reason or "Every consequential creative mutation remains subject to human authority and re-verification.")
            ),
        )


def apply_authorized_world(
    package: ProductionPackage,
    evidence: list[EvidenceRecord],
    world: World,
    *,
    case_revision: int,
) -> tuple[ProductionPackage, list[EvidenceRecord], list[str]]:
    """Apply a human-authorized production mutation.

    Crucially, authority does not create factual evidence. Any changed/continued asset
    enters a new revision and therefore must pass PROOF again.
    """
    assets: dict[str, Asset] = {a.id: a.model_copy(deep=True) for a in package.assets}
    changes: list[str] = []
    for intervention in world.interventions:
        asset = assets.get(intervention.asset_id)
        if not asset:
            continue
        action = intervention.action.lower()
        if action.startswith("remove"):
            assets.pop(asset.id, None)
            changes.append(f"Removed {asset.label} from all coupled usages.")
        elif action.startswith("replace"):
            asset.label = f"Replacement for {asset.label}"
            asset.notes = (asset.notes + " Human-authorized replacement requires fresh rights evidence.").strip()
            asset.internal_documented = False
            assets[asset.id] = asset
            changes.append(f"Replaced {intervention.asset_id}; prior evidence is historical only.")
        elif action.startswith("verify"):
            asset.notes = (asset.notes + " Human authorized a verification/negotiation step; no license is presumed.").strip()
            assets[asset.id] = asset
            changes.append(f"Authorized verification for {intervention.asset_id}; PROOF must still obtain evidence.")
        elif action.startswith("delay"):
            changes.append(f"Authorized schedule/territory change for {intervention.asset_id}; scope must be reverified.")
        else:
            asset.notes = (asset.notes + f" Authorized intervention: {intervention.description}").strip()
            assets[asset.id] = asset
            changes.append(f"Applied bounded intervention to {intervention.asset_id}; fresh evidence required.")

    revised_package = package.model_copy(update={"assets": list(assets.values())}, deep=True)
    # Preserve old evidence exactly as historical lineage. Never relabel it to the new revision.
    revised_evidence = [e.model_copy(deep=True) for e in evidence]
    return revised_package, revised_evidence, changes
