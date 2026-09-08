# Release Path — Agentic Cinema 2026

**Agentic Cinema · Parallel track · v0.3 · MIT licensed**

Release Path is a governed media-production decision system that asks a harder question than ordinary clearance tooling:

> If the current production world is blocked, what is the smallest evidence-backed change that moves it toward release while respecting deadline, territory, creative intent, evidence quality, and human authority?

## What is different

Most agents run one reasoning loop. Release Path uses a **state-dependent cognitive router**. The problem state determines whether the system should frame the objective, map dependencies, verify evidence, attack assumptions, test edge cases, widen the geographic frame, generate counterfactual production worlds, choose a minimum useful intervention, or stop for human authority.

Public modes demonstrated:

- **NATE** — practical objective framing and post-optimization reality check
- **ECHO** — dependency graph and counterfactual consequence propagation
- **PROOF** — revision-bound evidence, provenance, freshness and source-family independence
- **OBELISK** — structural attack on the current answer
- **DEVIL** — edge-case failure search
- **TGC** — distribution/territory evidence-frame expansion
- **COUNTERFACTUAL** — bounded candidate production changes
- **MINIMUM** — Pareto + minimum-useful-action selection
- **AUTHORITY** — explicit human permission before consequential creative mutation
- **DISTILLATION** — judge-safe decision receipt without private prompt disclosure

## Hackathon integrations

The live path is designed around:

1. **Parallel Search** for fresh, traceable web evidence at runtime.
2. **Gemini / Google ADK** for bounded counterfactual proposal/orchestration.
3. **Deterministic routing and evaluation** for consequence propagation, Pareto/minimum-useful-action selection, and fail-closed status.
4. **Human authority** for consequential creative changes. Approval creates a new production revision and triggers PROOF again.

Gemini proposes possibilities. The deterministic engine evaluates consequences. External search results remain evidence inputs, not automatic truth.

## Safety boundary

Release Path is decision support, **not legal advice**. `HOLD`, `CONDITIONAL`, and `GREENLIGHT` are production decision states, not certifications of copyright ownership or legal clearance.

## Source

The exact locally verified v0.3 source is preserved in `release_path_v0.3.zip`.

SHA-256:

```text
c8d9119dce5cf84a974946e96d30829b69d50dc62161eddccde4a7e24b8a8409
```

This branch includes an automated materialization workflow that expands the exact archive into normal browseable source files. If the workflow is unavailable, download the archive and run:

```bash
python extract_source.py
```

## Local verification

Before external release work, the exact archive passed **26/26 automated tests**, Python compilation, JavaScript syntax checking, FastAPI health smoke testing, deterministic mode routing, server-issued authority validation, and revision 1 → authority → revision 2 re-verification.

Live partner/model claims are intentionally **not** represented as verified until credentialed public reproduction succeeds.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open `http://127.0.0.1:8000`.

For deterministic mock-corpus demonstration, use **Run deterministic demo**. For the competition live path, configure the environment documented in `.env.example` and `docs/LIVE_VERIFICATION.md`.

## Demo thesis

**Existing clearance systems tell a producer where the wall is. Release Path models the smallest evidence-backed path around it.**
