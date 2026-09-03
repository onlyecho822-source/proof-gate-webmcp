# Test receipt

**Project:** Proof Gate WebMCP v0.2  
**Verification date:** 2026-09-03  
**Command:** `node --test tests/*.test.mjs`

## GitHub Actions receipt

- Workflow: **Proof Gate CI**
- Run: **33727373872**
- Commit: `93f10d067ac777e352f0aa01518c0cc3012d9219`
- Runner: Ubuntu 24.04 / Node 22.23.2
- Status: **SUCCESS**
- Tests: **26**
- Passed: **26**
- Failed: **0**
- Skipped: **0**
- Duration reported by Node test runner: **148.430269 ms**

Workflow receipt:
https://github.com/onlyecho822-source/proof-gate-webmcp/actions/runs/33727373872

Coverage includes:

- deterministic evidence engine behavior
- claim-revision binding
- duplicate source-family collapse
- context-evidence confidence isolation
- unsafe URL rejection
- embedded-credential URL rejection
- unknown and future-date behavior
- bounded contradiction analysis
- persisted-state revalidation
- bounded evidence ledger
- UI provenance contracts
- safe external-link rel attributes
- no remote script dependency
- WebMCP untrusted-content annotations
- WebMCP registration/enumeration contract
- `readOnlyHint` mutation semantics

## Scope boundary

This receipt proves that GitHub Actions checked out the public repository and successfully ran the 26 automated tests against that commit. It does **not** prove a native browsing-agent invocation in a production WebMCP browser; that remains a separate external verification gate.
