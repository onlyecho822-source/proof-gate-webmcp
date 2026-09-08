from datetime import datetime, timezone

from app.demo_data import sample_package, sample_evidence
from app.engine import ReleasePathEngine, apply_authorized_world
from app.models import Intervention, ProductionPackage


def fixed_now():
    return datetime(2026, 9, 8, 15, 0, tzinfo=timezone.utc)


def test_router_is_state_dependent_and_spirals():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    modes = [event.mode.value for event in decision.mode_trace]
    assert modes[0:4] == ["NATE", "ECHO", "PROOF", "OBELISK"]
    assert modes.count("ECHO") >= 3
    assert modes.count("PROOF") >= 2
    for required in {"DEVIL", "TGC", "COUNTERFACTUAL", "MINIMUM", "AUTHORITY", "DISTILLATION"}:
        assert required in modes


def test_router_skips_counterfactuals_when_nothing_is_blocked():
    package = ProductionPackage(title="Empty production", objective="Ship an empty internal slate", assets=[])
    decision = ReleasePathEngine(package, now=fixed_now()).decide([])
    modes = [e.mode.value for e in decision.mode_trace]
    assert decision.current_status == "GREENLIGHT"
    assert "COUNTERFACTUAL" not in modes
    assert "AUTHORITY" not in modes
    assert modes[-1] == "DISTILLATION"


def test_demo_does_not_issue_unqualified_greenlight():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    assert decision.current_status in {"HOLD", "CONDITIONAL"}
    assert decision.open_constraints


def test_counterfactuals_are_bounded_and_recommendation_is_pareto_valid():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    assert 1 <= len(decision.worlds) <= 12
    recommended = next(w for w in decision.worlds if w.id == decision.recommended_world_id)
    assert recommended.pareto_optimal is True
    assert not recommended.remaining_constraints


def test_recommended_world_requires_human_authority():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    assert decision.authority_required is True
    assert decision.recommended_world_id is not None


def test_duplicate_source_family_becomes_constraint():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    kinds = {(c.asset_id, c.kind) for c in decision.open_constraints}
    assert ("song-a", "source-concentration") in kinds


def test_cross_deliverable_dependency_is_explicit():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    kinds = {(c.asset_id, c.kind) for c in decision.open_constraints}
    assert ("song-a", "cross-deliverable-dependency") in kinds


def test_tgc_expands_distribution_evidence_frame():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    assert decision.research_requests
    req = next(r for r in decision.research_requests if r.asset_id == "song-a")
    assert "United Kingdom" in req.territories
    assert any(c.kind == "evidence-frame-insufficient" for c in decision.open_constraints)


def test_proof_excludes_prior_revision_evidence():
    evidence = [e.model_copy(update={"claim_revision": 1}) for e in sample_evidence()]
    decision = ReleasePathEngine(sample_package(), case_revision=2, now=fixed_now()).decide(evidence)
    assert any(c.kind == "historical-evidence-excluded" and c.status == "resolved" for c in decision.all_constraints)
    assert any(c.kind == "evidence-gap" for c in decision.open_constraints)


def test_authorized_remove_world_creates_new_revision_then_reverifies():
    package = sample_package()
    evidence = sample_evidence()
    first = ReleasePathEngine(package, now=fixed_now()).decide(evidence)
    world = next(w for w in first.worlds if w.id == first.recommended_world_id)
    assert all(i.action == "remove usage" for i in world.interventions)
    revised_package, revised_evidence, changes = apply_authorized_world(
        package, evidence, world, case_revision=1
    )
    assert changes
    assert revised_package.assets == []
    second = ReleasePathEngine(revised_package, case_revision=2, now=fixed_now()).decide(revised_evidence)
    assert second.current_status == "GREENLIGHT"
    assert second.case_revision == 2
    assert second.mode_trace[-1].mode.value == "DISTILLATION"


def test_authority_does_not_fake_permission_for_verify_action():
    package = sample_package()
    evidence = sample_evidence()
    first = ReleasePathEngine(package, now=fixed_now()).decide(evidence)
    verify_world = next(w for w in first.worlds if all(i.action.startswith("verify") for i in w.interventions))
    revised_package, revised_evidence, _ = apply_authorized_world(package, evidence, verify_world, case_revision=1)
    second = ReleasePathEngine(revised_package, case_revision=2, now=fixed_now()).decide(revised_evidence)
    assert second.current_status != "GREENLIGHT"
    assert any(c.kind == "evidence-gap" for c in second.open_constraints)


def test_nate_rejects_world_that_misses_real_deadline():
    package = sample_package().model_copy(update={"release_deadline": "2026-09-08T16:00:00Z"})
    decision = ReleasePathEngine(package, now=fixed_now()).decide(sample_evidence())
    assert decision.current_status == "HOLD"
    assert any(e.mode.value == "NATE" and e.state_signal == "recommended-world-misses-objective" for e in decision.mode_trace)


def test_external_counterfactuals_can_be_scored_without_model_self_grading():
    package = sample_package()
    provisional = ReleasePathEngine(package, now=fixed_now()).decide(sample_evidence())
    by_asset = {}
    for c in provisional.open_constraints:
        if c.asset_id != "case":
            by_asset.setdefault(c.asset_id, []).append(c.id)
    external = [
        Intervention(
            id=f"x-{asset}", asset_id=asset, action="replace asset", description="bounded external candidate",
            estimated_cost=10, delay_hours=1, creative_disruption=2, rights_uncertainty=1,
            irreversibility=1, clears_constraints=ids, requires_human_approval=True,
        ) for asset, ids in by_asset.items()
    ]
    decision = ReleasePathEngine(package, now=fixed_now()).decide(sample_evidence(), external)
    assert decision.current_status == "CONDITIONAL"
    assert any(e.mode.value == "COUNTERFACTUAL" and "Gemini-generated" in e.output_summary for e in decision.mode_trace)


def test_distillation_outputs_public_receipt_not_private_prompt_material():
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(sample_evidence())
    joined = " ".join(decision.public_receipt).lower()
    assert "open blockers" in joined
    assert "private prompts" in joined
    assert "chain of thought" not in joined


def test_tgc_accepts_explicit_revision_bound_global_scope():
    evidence = [e.model_copy() for e in sample_evidence()]
    for e in evidence:
        e.scope_territories = ["__global__"]
    decision = ReleasePathEngine(sample_package(), now=fixed_now()).decide(evidence)
    assert decision.research_requests == []
    assert not any(c.kind == "evidence-frame-insufficient" for c in decision.open_constraints)
