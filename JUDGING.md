# WebMCP judging map

Proof Gate is designed around the four equally weighted WebMCP judging dimensions.

## 1. WebMCP Leverage

The agent is not using WebMCP as a cosmetic wrapper around an existing endpoint. The application exposes stateful case semantics directly through six typed tools. Human UI actions and agent tool calls mutate the same case state and use the same evidence engine.

The demo should visibly show:

- a human framing the claim
- an agent reading the same case
- an agent adding evidence
- the UI updating without a second hidden state
- the agent identifying conflicts and evaluating
- the human inspecting the resulting lineage

## 2. Execution

The application is deliberately small and testable rather than feature-heavy.

Execution evidence:

- static browser application with no remote runtime dependency
- deterministic evidence engine
- claim-revision binding
- source-family concentration controls
- explicit uncertainty and freshness handling
- bounded ledger/conflict surfaces
- WebMCP annotations for untrusted content
- automated engine, red-team, UI, and WebMCP contract tests

## 3. Potential Impact

The generic problem is broader than fact checking: agents increasingly interact with consequential web workflows, but application state, provenance, and uncertainty often disappear behind DOM automation or model memory.

Proof Gate demonstrates a pattern for accountable agent collaboration in procurement, research, compliance, claims review, investigations, customer operations, and other evidence-heavy workflows.

## 4. Creativity & Ambition

The project's ambition is architectural rather than decorative:

> Most competitors build intelligent agents. We build accountable intelligence.

The distinctive pattern is the Global Compass signature:

```text
SEE REALITY
→ PRESERVE EVIDENCE
→ UNDERSTAND RELATIONSHIPS
→ SEPARATE CAPABILITY FROM AUTHORITY
→ VERIFY WHAT ACTUALLY HAPPENED
→ LEARN WITHOUT REWRITING HISTORY
```

The Distillation Protocol makes the WebMCP boundary itself part of the product: raw external content is not silently promoted to truth, and internal state is exposed through narrow auditable operations rather than unconstrained agent action.

## Three-minute proof sequence

1. Open Proof Gate and show WebMCP status / six tools.
2. Load the fictional vendor claim demo.
3. Ask the agent for the case.
4. Show the same evidence ledger in the human UI.
5. Have the agent identify conflicts.
6. Revise the claim and demonstrate that old evidence stays visible but no longer contaminates the verdict.
7. Add one new evidence record through the agent.
8. Evaluate and show the deterministic result + audit lineage.
9. Export the case.
10. Close on: **Accountable intelligence, not merely intelligent agents.**
