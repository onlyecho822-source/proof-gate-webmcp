# Release Path v0.3 — Public Architecture

## Core principle

The production problem chooses the next cognitive mode. The application does not blindly execute a fixed sequence.

```text
INPUT + CURRENT STATE + EVIDENCE
              │
              ▼
        STATE ROUTER
              │
   ┌──────────┼───────────┐
   ▼          ▼           ▼
 NATE       ECHO        PROOF
   ▲          │           │
   │          ▼           ▼
   │       OBELISK ◄── evidence
   │          │
   │          ▼
   │        DEVIL
   │          │
   │          ▼
   │         TGC ───────► PROOF
   │          │
   └── COUNTERFACTUAL
              │
              ▼
             ECHO
              │
              ▼
           MINIMUM
              │
              ▼
             NATE
              │
              ▼
          AUTHORITY
              │
              ▼
        new revision
              │
              ▼
            PROOF
```

DISTILLATION produces the external receipt at the end of every decision cycle.

## Router behavior

The router evaluates state flags after every mode. Examples:

- objective unframed → NATE
- graph missing or dirtied by adversarial findings → ECHO
- evidence unverified or scope changed → PROOF
- structural assumptions not challenged → OBELISK
- costly edge cases not tested → DEVIL
- global/distribution frame not tested → TGC
- blockers exist without intervention candidates → COUNTERFACTUAL
- interventions exist without propagated worlds → ECHO
- worlds exist without minimum-useful-action selection → MINIMUM
- candidate selected but not checked against practical objective → NATE
- consequential change proposed → AUTHORITY
- external explanation required → DISTILLATION

The test suite proves that ECHO and PROOF can be revisited and that clean cases skip modes that are unnecessary.

## Evidence revisions

Every evidence record carries `claim_revision`. A production mutation creates a new revision. Old evidence is preserved as history but cannot automatically support the new production world.

This prevents an old fact about an old edit from silently becoming evidence for a changed edit.

## Minimum useful action

Release Path does not collapse every objective into one scalar score.

For viable alternate worlds it first computes a Pareto set across:

- estimated cost
- schedule delay
- creative disruption
- rights uncertainty
- irreversibility
- intervention count
- affected dependency edges

It then prefers the smallest intervention/graph disturbance and uses the producer's explicit weights only as a later tie-breaker.

NATE can still reject the mathematical favorite if it misses the actual deadline.

## External intelligence boundary

- Parallel Search supplies fresh web context.
- Gemini proposes bounded counterfactual interventions.
- Deterministic code performs routing and evaluation.
- Human authority controls consequential creative mutation.

## Private/public boundary

The public repository demonstrates the mode geometry and state router required for the hackathon. It does not contain broader cross-domain private orchestration prompts, personal data, or unrelated internal project material.
