from .models import ProductionPackage, Asset, EvidenceRecord


def sample_package() -> ProductionPackage:
    return ProductionPackage(
        title="Friday Cut — Mock Production",
        objective=(
            "Deliver the film and its trailer this Friday with the smallest creative disruption, "
            "without treating unresolved rights evidence as clearance."
        ),
        release_deadline="2026-09-11T17:00:00Z",
        assets=[
            Asset(
                id="song-a", kind="music", label="Neon Avenue (fictional song)",
                usage_locations=["Scene 12", "Trailer"],
                territories=["United States", "United Kingdom"],
                search_queries=[
                    '"Neon Avenue" fictional music audiovisual license rights',
                    '"Neon Avenue" soundtrack permission master publishing',
                ],
                notes="Mock asset used only to demonstrate the reasoning architecture.",
            ),
            Asset(
                id="photo-b", kind="archive-photo", label="Harbor 1974 (fictional archive photo)",
                usage_locations=["Scene 44"],
                territories=["United States", "France"],
                search_queries=[
                    '"Harbor 1974" fictional archive photo license audiovisual rights',
                    '"Harbor 1974" archive permission France distribution',
                ],
                notes="Mock asset with an intentionally incomplete territory record.",
            ),
        ],
    )


def sample_evidence() -> list[EvidenceRecord]:
    # Entire corpus is intentionally fictitious. It proves engine behavior, not rights facts.
    return [
        EvidenceRecord(
            id="e-song-1", asset_id="song-a", source_label="Mock Rights Registry",
            source_url="https://rights.example.test/song-a", source_family="rights.example.test",
            excerpt="Mock record says domestic audiovisual use is under negotiation and no UK scope is established.",
            publish_date="2026-09-01", stance="context", provenance="mock-corpus", reliability=3,
            claim_revision=1, scope_territories=["United States"],
        ),
        EvidenceRecord(
            id="e-song-2", asset_id="song-a", source_label="Mock Rights Registry Syndication",
            source_url="https://rights.example.test/song-a-copy", source_family="rights.example.test",
            excerpt="A derivative mock record repeats the same domestic negotiation statement.",
            publish_date="2026-09-01", stance="context", provenance="mock-corpus", reliability=2,
            claim_revision=1, scope_territories=["United States"],
        ),
        EvidenceRecord(
            id="e-photo-1", asset_id="photo-b", source_label="Mock Archive Card",
            source_url="https://archive.example.test/photo-b", source_family="archive.example.test",
            excerpt="Mock card documents United States editorial use only; France is not listed.",
            publish_date="2026-08-28", stance="context", provenance="mock-corpus", reliability=4,
            claim_revision=1, scope_territories=["United States"],
        ),
    ]
