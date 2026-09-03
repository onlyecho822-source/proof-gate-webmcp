# WebMCP submission draft

## Project

**Proof Gate**

**Tagline:** Accountable intelligence for the open web: humans and agents build, challenge, and verify the same evidence-backed case.

## Submitter type

Individual

## App status

New

## Why this is a strong fit for WebMCP

Proof Gate is stateful by design. A case contains a claim revision, decision context, evidence records, provenance, conflicts, deterministic evaluation, and an audit lineage. Without WebMCP, a browsing agent has to infer those semantics from page controls and maintain a second representation of the case.

Proof Gate exposes six narrow application operations through `document.modelContext.registerTool(...)`. Those tools use the same state and deterministic evidence engine as the visible human UI. A person and an agent can therefore collaborate on one inspectable case instead of operating on two drifting interpretations.

## Better user experience

The human can see exactly what evidence exists, which claim revision it belongs to, where sources conflict, which records come from the same source family, and how the verdict was produced. The agent can manipulate the same structured state without reverse-engineering the DOM.

Changing the claim creates a new revision. Earlier evidence remains visible for lineage but cannot silently contaminate the new verdict.

## What becomes possible

A human can frame and challenge a case while an agent structures evidence, identifies conflicts, evaluates the current revision, and exports the record. Both sides work on one source of application state.

This makes the agent useful without making it an unaccountable source of truth.

## WebMCP implementation

The application registers:

- `proofgate.get_case`
- `proofgate.set_claim`
- `proofgate.add_evidence`
- `proofgate.identify_conflicts`
- `proofgate.evaluate_case`
- `proofgate.export_case`

The WebMCP handlers call the same pure JavaScript evidence engine used by the visible UI. Evidence-derived outputs use `untrustedContentHint`; mutating tools are not incorrectly marked read-only. When supported, the page checks tool enumeration with `getTools()` after registration.

## Distillation Protocol

Proof Gate treats the WebMCP boundary as a governance filter. Raw external content enters as attributable structured evidence rather than automatic truth. Internal case state exits through narrow typed operations rather than unconstrained agent actions.

The system preserves the difference between intended, reported, and observed state and is designed to represent: “I do not know yet, and here is exactly what evidence would resolve it.”

## AI tools used

ChatGPT was used for architecture review, adversarial testing, implementation assistance, documentation, and submission preparation.

## Learning level

Significant

## Career AI value

Yes

## Final fields still requiring external receipts

- live public application URL
- public YouTube demo URL under 3 minutes with audio
- exact WebMCP agent/client(s) used in the real browser verification
- final country-of-residence selection supplied truthfully on the Devpost form

## Public repository

https://github.com/onlyecho822-source/proof-gate-webmcp

Do not submit this draft as final until the live URL, native WebMCP verification, and public video have receipts.
