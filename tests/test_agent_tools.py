from app.agent import release_guardrail_tool, evaluate_release_package_tool
from app.demo_data import sample_package, sample_evidence


def test_guardrail_blocks_fake_greenlight():
    out = release_guardrail_tool("GREENLIGHT", evidence_count=0, unresolved_constraints=2)
    assert out["allowed"] is False
    assert out["status"] == "HOLD"


def test_deterministic_tool_returns_trace():
    out = evaluate_release_package_tool(
        sample_package().model_dump(),
        [e.model_dump() for e in sample_evidence()],
    )
    assert out["mode_trace"][0]["mode"] == "NATE"
    assert out["current_status"] in {"HOLD", "CONDITIONAL"}
