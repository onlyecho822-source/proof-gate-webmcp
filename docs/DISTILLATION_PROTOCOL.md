# Distillation Protocol — the Proof Gate governance boundary

## Purpose

The Distillation Protocol defines what may cross between the external web/tool environment and Proof Gate's governed case state.

Its job is simple: **raw noise does not become trusted state merely because it arrived through a tool, model, API, or user interface.**

## Inbound filter

External observations are normalized before they influence a case:

1. preserve the supplied observation or excerpt
2. record source label and provenance
3. classify stance and source type
4. preserve unknown values as unknown
5. reject structurally invalid inputs such as unsafe URLs or future observation dates
6. bind the evidence to the current claim revision
7. mark evidence-derived WebMCP content as untrusted

Proof Gate does not silently promote a report into an independently verified fact.

## Outbound filter

The application does not expose an unconstrained "do anything" agent surface. It exposes six narrow WebMCP tools with typed schemas and defined state effects.

That boundary constrains what an agent may read or change and leaves the resulting transition visible in the same state the human inspects.

## Anti-magic rule

The system must be able to represent:

> I do not know yet, and here is exactly what evidence would resolve it.

Therefore:

- API success is a reported state, not automatically an observed real-world outcome
- model output is not automatically evidence
- user input is preserved as supplied rather than silently upgraded to independently verified fact
- tool output remains attributable to the tool/source that produced it
- uncertainty is carried forward rather than erased for presentation convenience

## Reality triangle

```text
INTENDED
what the workflow was trying to establish or permit
    ↓
REPORTED
what a person, model, API, or tool says happened
    ↓
OBSERVED
what the recorded evidence actually supports
```

Proof Gate focuses on keeping these categories distinguishable. It does not claim that the application independently observes the external world; instead it preserves the evidence needed for a human and agent to inspect the gap.

## Why this matters for WebMCP

WebMCP gives the agent a first-class application interface. The Distillation Protocol makes that interface governed:

- shared state instead of hidden parallel state
- typed evidence instead of DOM inference
- explicit revision boundaries instead of silent carry-over
- narrow state transitions instead of unconstrained action
- visible uncertainty instead of fake omniscience
- exportable lineage instead of an unexplained answer

This is the distinction between merely capable agents and accountable intelligence.
