from app.evidence import infer_scope_territories, normalize_parallel_results


def test_scope_inference_requires_positive_rights_language():
    targets = ["United States", "United Kingdom"]
    assert infer_scope_territories("This page mentions United Kingdom but does not grant rights.", targets) == []
    assert infer_scope_territories("Licensed in United Kingdom for audiovisual use.", targets) == ["United Kingdom"]
    assert infer_scope_territories("Worldwide license granted for audiovisual use.", targets) == ["__global__"]


def test_parallel_normalization_carries_explicit_scope_hint():
    payload = {"results":[{"url":"https://example.com/a","title":"License","excerpts":["Rights for United States are granted for this use."],"publish_date":"2026-09-01"}]}
    records = normalize_parallel_results("a", payload, claim_revision=2, target_territories=["United States"])
    assert records[0].claim_revision == 2
    assert records[0].scope_territories == ["United States"]
