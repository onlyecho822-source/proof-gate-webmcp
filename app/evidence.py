from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from .models import EvidenceRecord, Constraint, Mode, Asset, ResearchRequest

TRACKING_KEYS = {"gclid", "fbclid", "msclkid", "mc_cid", "mc_eid"}
GLOBAL_TOKENS = ("worldwide", "global", "all territories", "international rights", "world rights")
POSITIVE_SCOPE_TOKENS = (
    "license", "licensed", "rights", "authorized", "authorised", "permission", "permitted",
    "territory", "territories", "grant", "granted", "covers", "covered", "available for",
)


def normalize_url(raw: str) -> tuple[str, str]:
    raw = (raw or "").strip()
    if not raw:
        return "", ""
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise ValueError("Evidence URLs must use http or https")
    if "@" in parts.netloc:
        raise ValueError("Evidence URL must not contain embedded credentials")
    host = (parts.hostname or "").lower()
    query = [
        (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in TRACKING_KEYS
    ]
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", urlencode(query), ""))
    return normalized, f"host:{host}"


def date_state(value: str | None, now: datetime | None = None) -> str:
    if not value:
        return "unknown"
    now = now or datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return "unknown"
    if dt > now:
        return "future"
    return "stale" if (now - dt).days > 365 else "current"


def infer_scope_territories(text: str, targets: list[str]) -> list[str]:
    """Conservative scope extraction.

    A territory name merely appearing in a page is not proof that a license/permission
    covers it. We require rights/permission vocabulary in the same normalized text.
    """
    normalized = re.sub(r"\s+", " ", (text or "").lower())
    if not any(token in normalized for token in POSITIVE_SCOPE_TOKENS):
        return []
    if any(token in normalized for token in GLOBAL_TOKENS):
        return ["__global__"]
    found: list[str] = []
    for territory in targets:
        if territory.lower() in normalized:
            found.append(territory)
    return found


def normalize_parallel_results(
    asset_id: str,
    payload: dict,
    *,
    claim_revision: int = 1,
    target_territories: list[str] | None = None,
    provenance: str = "parallel-search",
) -> list[EvidenceRecord]:
    records: list[EvidenceRecord] = []
    targets = target_territories or []
    for idx, result in enumerate(payload.get("results", [])[:20], 1):
        url = result.get("url") or ""
        try:
            normalized_url, family = normalize_url(url)
        except ValueError:
            normalized_url, family = "", ""
        excerpts = result.get("excerpts") or []
        if isinstance(excerpts, str):
            excerpts = [excerpts]
        excerpt = " \n".join(str(x) for x in excerpts if x)[:4500]
        if not excerpt:
            excerpt = str(result.get("text") or result.get("snippet") or "")[:4500]
        source_label = str(result.get("title") or result.get("name") or normalized_url or f"Parallel result {idx}")[:300]
        publish_date = result.get("publish_date") or result.get("published_at") or result.get("date")
        scope = infer_scope_territories(f"{source_label} {excerpt}", targets)
        records.append(EvidenceRecord(
            id=f"parallel-{asset_id}-{idx}",
            asset_id=asset_id,
            source_label=source_label,
            source_url=normalized_url,
            excerpt=excerpt or "Parallel returned a result without an extractable excerpt.",
            publish_date=str(publish_date)[:40] if publish_date else None,
            stance="context",
            source_family=family or f"parallel-result:{idx}",
            provenance=provenance,
            reliability=3,
            claim_revision=claim_revision,
            scope_territories=scope,
        ))
    return records


def evaluate_evidence(
    asset: Asset,
    records: list[EvidenceRecord],
    *,
    claim_revision: int = 1,
    now: datetime | None = None,
) -> list[Constraint]:
    issues: list[Constraint] = []
    all_asset_records = [r for r in records if r.asset_id == asset.id]
    active = [r for r in all_asset_records if r.claim_revision == claim_revision]
    historical = [r for r in all_asset_records if r.claim_revision != claim_revision]

    if historical:
        issues.append(Constraint(
            id=f"{asset.id}:historical-evidence-excluded:r{claim_revision}", asset_id=asset.id,
            kind="historical-evidence-excluded", severity="low", status="resolved",
            message=f"{len(historical)} evidence record(s) belong to an older production revision and are preserved as history only.",
            blocks=[], introduced_by=Mode.PROOF, claim_revision=claim_revision,
        ))

    if not active and not asset.internal_documented:
        issues.append(Constraint(
            id=f"{asset.id}:evidence-gap:r{claim_revision}", asset_id=asset.id, kind="evidence-gap", severity="critical",
            message="No revision-bound evidence is present for this rights-sensitive asset.",
            blocks=asset.usage_locations + asset.territories, introduced_by=Mode.PROOF, claim_revision=claim_revision,
        ))
        return issues

    if asset.internal_documented and not active:
        issues.append(Constraint(
            id=f"{asset.id}:internal-documentation:r{claim_revision}", asset_id=asset.id, kind="internal-documentation",
            severity="medium", status="unknown",
            message="The production marks this asset as internally documented, but the evidence packet is not attached to this prototype case.",
            blocks=asset.usage_locations, introduced_by=Mode.PROOF, claim_revision=claim_revision,
        ))
        return issues

    families = Counter(r.source_family or r.source_label.lower() for r in active)
    concentrated = [family for family, count in families.items() if count > 1]
    if concentrated:
        issues.append(Constraint(
            id=f"{asset.id}:source-concentration:r{claim_revision}", asset_id=asset.id, kind="source-concentration", severity="high",
            message=f"Multiple records collapse to the same source family ({', '.join(concentrated)}); repetition is not independent corroboration.",
            blocks=["independent corroboration"], introduced_by=Mode.PROOF, claim_revision=claim_revision,
        ))

    if any(r.stance == "supports" for r in active) and any(r.stance == "contradicts" for r in active):
        issues.append(Constraint(
            id=f"{asset.id}:direct-contradiction:r{claim_revision}", asset_id=asset.id, kind="direct-contradiction", severity="critical",
            message="The active evidence packet contains both supporting and contradicting records.",
            blocks=asset.usage_locations, introduced_by=Mode.PROOF, claim_revision=claim_revision,
        ))

    for rec in active:
        freshness = date_state(rec.publish_date, now)
        if freshness == "future":
            issues.append(Constraint(
                id=f"{asset.id}:future-date:{rec.id}:r{claim_revision}", asset_id=asset.id, kind="future-date", severity="high",
                message=f"Evidence record {rec.id} has a future date and cannot be treated as current evidence.",
                blocks=["freshness"], introduced_by=Mode.PROOF, claim_revision=claim_revision,
            ))
        elif freshness == "stale":
            issues.append(Constraint(
                id=f"{asset.id}:stale:{rec.id}:r{claim_revision}", asset_id=asset.id, kind="stale-evidence", severity="medium",
                message=f"Evidence record {rec.id} is more than one year old and should be refreshed.",
                blocks=["freshness"], introduced_by=Mode.PROOF, claim_revision=claim_revision,
            ))
        elif freshness == "unknown":
            issues.append(Constraint(
                id=f"{asset.id}:unknown-date:{rec.id}:r{claim_revision}", asset_id=asset.id, kind="unknown-date", severity="low",
                status="unknown", message=f"Evidence record {rec.id} has no verifiable publication/observation date.",
                blocks=["freshness confidence"], introduced_by=Mode.PROOF, claim_revision=claim_revision,
            ))
    return issues


def build_tgc_research_requests(
    assets: list[Asset],
    evidence: list[EvidenceRecord],
    *,
    claim_revision: int,
) -> list[ResearchRequest]:
    requests: list[ResearchRequest] = []
    for asset in assets:
        targets = [t for t in asset.territories if t and t.lower() != "worldwide"]
        if not targets:
            continue
        active = [r for r in evidence if r.asset_id == asset.id and r.claim_revision == claim_revision]
        if any("__global__" in r.scope_territories for r in active):
            continue
        covered = {t for r in active for t in r.scope_territories}
        missing = [t for t in targets if t not in covered]
        if missing:
            base = asset.search_queries[0] if asset.search_queries else asset.label
            requests.append(ResearchRequest(
                asset_id=asset.id,
                reason="Available evidence does not explicitly cover the intended distribution frame.",
                territories=missing,
                search_queries=[f"{base} {territory} rights license permission" for territory in missing][:4],
            ))
    return requests
