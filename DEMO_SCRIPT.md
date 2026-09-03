# Proof Gate demo script — target 2:20–2:40

## 0:00–0:15 — Hook

**Narration:**

Most agents are optimized to act. Proof Gate is optimized to make action inspectable. It is a WebMCP-native evidence workspace where a human and an agent build the same versioned case.

Show the page header and WebMCP status.

## 0:15–0:35 — The shared case

Load the fictional vendor demo.

**Narration:**

The human sees the claim, decision context, evidence ledger, conflicts, deterministic verdict, and audit lineage. The agent does not get a hidden parallel copy. It sees six typed WebMCP tools operating on this exact same state.

Show the six registered tool names.

## 0:35–0:55 — Read through WebMCP

Ask the browsing agent to call `proofgate.get_case` and summarize the current claim and evidence count.

**Narration:**

Instead of scraping labels and guessing which control matters, the agent reads application semantics directly.

## 0:55–1:20 — Conflict and uncertainty

Call `proofgate.identify_conflicts`.

Point to the contradicting customer export and the contextual measurement note.

**Narration:**

Proof Gate preserves contradiction instead of averaging it away. API, model, user, and tool statements enter through the Distillation Protocol as attributable evidence, not automatic truth.

## 1:20–1:45 — Revision boundary

Use `proofgate.set_claim` to materially revise the claim.

Show old evidence becoming historical-only and the verdict dropping back to insufficient.

**Narration:**

This is the part ordinary chat memory gets wrong. When the claim changes, old evidence stays visible for lineage but cannot silently migrate into the new claim.

## 1:45–2:05 — Agent adds evidence

Use `proofgate.add_evidence` with a fictional HTTP source and a current valid date.

Show the human UI update immediately.

**Narration:**

The agent and human are working on one state, with provenance, uncertainty, and claim binding enforced by the application.

## 2:05–2:25 — Evaluate and audit

Call `proofgate.evaluate_case`, then show the verdict and new audit event.

**Narration:**

The evaluator is deterministic and deliberately modest. It does not claim universal truth. It says what the recorded evidence supports and exposes what still does not reconcile.

## 2:25–2:40 — Close

Call `proofgate.export_case` or show Export JSON.

**Narration:**

Most competitors build intelligent agents. We build accountable intelligence: preserve evidence, expose uncertainty, verify state changes, and never rewrite the history that produced the decision.

## Recording rules

- public YouTube URL
- under 3 minutes
- audible narration
- show the working live app
- show at least one real WebMCP tool invocation in a compatible browser
- do not claim browser verification until that invocation is actually recorded
