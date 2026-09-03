# Local test receipt

**Project:** Proof Gate WebMCP v0.2  
**Verification date:** 2026-09-03  
**Command:** `node --test tests/*.test.mjs`

## Result

- Tests: **26**
- Passed: **26**
- Failed: **0**
- Skipped: **0**

Coverage includes:

- deterministic evidence engine behavior
- claim-revision binding
- duplicate source-family collapse
- context-evidence confidence isolation
- unsafe URL rejection
- unknown and future-date behavior
- bounded contradiction analysis
- persisted-state revalidation
- bounded evidence ledger
- UI provenance contracts
- WebMCP untrusted-content annotations
- WebMCP registration/enumeration contract
- `readOnlyHint` mutation semantics

## Scope boundary

This receipt proves the local implementation and mocked WebMCP contract tests passed. It does **not** claim a native browsing-agent invocation in a production WebMCP browser; that remains a separate external verification gate.
