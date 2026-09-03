# Proof Gate — accountable intelligence for the open web

**WebMCP Challenge candidate · v0.2 · MIT licensed**

Most agents are optimized to act. **Proof Gate is optimized to make action inspectable.**

Proof Gate is a browser-native evidence workspace where a human and a browsing agent work on the **same versioned case**. The human sees the claim, evidence ledger, conflicts, uncertainty, audit lineage, and deterministic verdict. A compatible browser agent sees six explicit WebMCP tools registered through `document.modelContext.registerTool(...)`.

## The contradiction

Web agents can often click and call tools, but a real evidence workflow needs more than capability. It needs shared state, provenance, uncertainty, revision boundaries, and a record of how a conclusion changed.

Proof Gate turns that contradiction into the product:

> **Most competitors build intelligent agents. We build accountable intelligence.**

## Why WebMCP

Without WebMCP, an agent must infer application semantics from labels and DOM controls and then maintain a parallel copy of the state. Proof Gate exposes narrow typed operations that mutate the same case state the human sees.

The demo is intentionally stateful: claim revisions, evidence provenance, conflict analysis, evaluation, and export are application semantics rather than DOM guesses.

## Six WebMCP tools

- `proofgate.get_case` — read the current versioned state and evaluation
- `proofgate.set_claim` — set or revise a claim; a changed claim creates a new revision
- `proofgate.add_evidence` — add structured evidence bound to the current claim revision
- `proofgate.identify_conflicts` — inspect contradiction, source concentration, freshness, and provenance gaps
- `proofgate.evaluate_case` — record a deterministic verdict for the current claim revision
- `proofgate.export_case` — export case state, evidence bindings, audit lineage, conflicts, and evaluation

## Distillation Protocol

Proof Gate treats the WebMCP boundary as a **governance filter**, not a magic tunnel into the application.

**Inbound:** raw user, tool, or web content becomes structured evidence with provenance and uncertainty before it can affect evaluation.

**Outbound:** internal state is exposed through narrow, typed, auditable tools rather than unconstrained agent actions.

That means an API response is a report, not automatically truth; an AI statement is a proposal, not automatically evidence; and untrusted evidence-derived content is explicitly marked for the browsing agent.

See [`docs/DISTILLATION_PROTOCOL.md`](docs/DISTILLATION_PROTOCOL.md).

## Global Compass signature

```text
SEE REALITY
→ PRESERVE EVIDENCE
→ UNDERSTAND RELATIONSHIPS
→ SEPARATE CAPABILITY FROM AUTHORITY
→ VERIFY WHAT ACTUALLY HAPPENED
→ LEARN WITHOUT REWRITING HISTORY
```

For this focused WebMCP build, that philosophy appears as explicit provenance, visible uncertainty, claim-revision boundaries, deterministic evaluation, narrow tools, and exportable lineage.

## v0.2 integrity rules

The red-team pass found failures that ordinary happy-path tests missed. v0.2 now enforces:

- **claim binding:** evidence is bound to the claim revision under which it was recorded
- **source-family independence:** repeated records from one source family cannot manufacture independent support
- **stance-specific confidence:** context records do not inflate support/refutation confidence
- **safe source URLs:** only `http`/`https` URLs are accepted; embedded credentials and executable schemes are rejected
- **truthful dates:** omitted dates remain unknown; future observation dates are rejected
- **bounded conflict analysis:** direct contradiction is aggregated instead of producing an O(n²) card explosion
- **bounded evidence ledger:** a case accepts at most 250 evidence records
- **restored-state validation:** persisted browser state is revalidated before rendering
- **WebMCP trust annotations:** outputs carrying evidence-derived content use `untrustedContentHint`
- **annotation semantics:** tools that record state changes are not mislabeled as read-only

## What the verdict means

The evaluator is deterministic, not a truth oracle. Its thresholds and source-family grouping are transparent **demo heuristics**. A host name is used as a conservative source-family proxy when a URL exists; that is not proof of real-world editorial independence.

The app does not browse or independently verify a source. It evaluates the evidence records entered into the current claim revision.

## Audit semantics

The browser state includes a versioned audit lineage for claim changes, evidence additions, and recorded evaluations. State transitions are inspectable and exportable.

It is **not cryptographically tamper-evident** and is not described as an immutable forensic ledger.

## Run locally

No build step or network dependency is required.

```bash
python3 -m http.server 8080
```

Open `http://localhost:8080`.

### WebMCP testing

The app registers through `document.modelContext.registerTool(...)` when the API is available. If `getTools()` is available, the page also checks whether all six registered names can be enumerated.

In a browser without native WebMCP, **Tool inspector** executes the exact same handlers locally.

A real native WebMCP browser invocation remains an external submission verification gate; mocked registration tests are not presented as a substitute.

## Tests

```bash
node --test tests/*.test.mjs
```

Current local verification: **26/26 passing tests** across the engine suite, red-team regressions, WebMCP contract checks, and UI contract checks. See [`TEST_RECEIPT.md`](TEST_RECEIPT.md).

## Submission state

- Open-source license: **MIT — complete**
- Public repository: **complete**
- Local automated tests: **26/26 passing**
- Live deployment: pending
- Native WebMCP browser verification: pending
- Public demo video: pending
- Final Devpost submission: pending

See `JUDGING.md`, `DEMO_SCRIPT.md`, `SUBMISSION_DRAFT.md`, and `docs/ARCHITECTURE.md`.
