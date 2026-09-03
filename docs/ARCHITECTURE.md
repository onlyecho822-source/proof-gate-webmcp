# Proof Gate architecture

## Center

Proof Gate is a browser-native evidence workspace where the human UI and WebMCP tools operate on one state object and one deterministic evidence engine.

```text
External human / browsing agent
            │
            ▼
   Distillation Protocol
            │
            ▼
      Shared case state
            │
    ┌───────┴────────┐
    ▼                ▼
Human UI       WebMCP tool layer
    │                │
    └───────┬────────┘
            ▼
 Deterministic evidence engine
            │
            ▼
Evidence → conflicts → verdict → audit lineage → export
```

## State model

A case preserves:

- `caseId`
- `claimRevision`
- exact `claim`
- `decisionContext`
- evidence records with stance, source type, source family, date, reliability, and revision binding
- conflict analysis
- deterministic verdict
- audit lineage
- engine/schema version

A material claim change increments the claim revision. Older evidence stays inspectable but is excluded from the new verdict until deliberately re-entered under that revision.

## Human → AI → machine

Proof Gate demonstrates the Global Compass separation in a narrow form:

**Human** frames or revises the claim, enters/inspects evidence, and challenges the result.

**Agent** uses explicit WebMCP operations to structure evidence, surface conflicts, evaluate, and export.

**Machine** enforces URL/date/schema constraints, revision binding, source-family grouping, scoring rules, and audit events deterministically.

The AI/tool layer does not gain truth authority merely because it can call a function.

## Distillation boundary

Inbound evidence is normalized and tagged before entering case state. Outbound WebMCP operations are narrow and typed. See `DISTILLATION_PROTOCOL.md`.

## Reality Triangle

Proof Gate keeps three states conceptually separate:

- **Intended** — what a decision/workflow seeks to establish
- **Reported** — what a source/tool/API/model says happened
- **Observed** — what the recorded evidence actually supports

The app does not pretend its own evaluator independently observes the outside world. It preserves the material needed to inspect the gap.

## WebMCP surface

The application registers six tools with `document.modelContext.registerTool(...)`:

1. `proofgate.get_case`
2. `proofgate.set_claim`
3. `proofgate.add_evidence`
4. `proofgate.identify_conflicts`
5. `proofgate.evaluate_case`
6. `proofgate.export_case`

The tool layer calls the same pure functions used by the UI; no parallel agent-only case exists.

## Security / integrity boundaries

- only HTTP/HTTPS source URLs
- no embedded URL credentials
- no future observation dates
- unknown dates preserved as unknown
- evidence limit of 250 records
- duplicate host/source family cannot manufacture independence
- context evidence does not inflate directional confidence
- direct contradiction is aggregated
- persisted state is normalized/revalidated
- evidence-derived tool outputs carry `untrustedContentHint`
- evaluation is correctly marked as state-changing because it records lineage

## Non-claims

Proof Gate does not claim:

- universal truth detection
- calibrated probabilities
- cryptographic immutability
- real-world editorial independence merely from different URLs
- native WebMCP browser success until independently tested in a compatible browser

Those boundaries are intentional. Accountable intelligence starts by refusing to counterfeit certainty.
