# Live Verification Procedure

A successful local test is not evidence that the competition integration works in production.

## Gate A — Parallel

1. Configure `PARALLEL_API_KEY`.
2. Start the app with `APP_MODE=live`.
3. Confirm `/api/runtime` reports `parallel_configured=true`.
4. Run **Run live Parallel + Gemini**.
5. Capture server logs showing the Search API request returned HTTP 2xx.
6. Confirm returned evidence has `provenance=parallel-search` or `parallel-search|tgc-scope-expansion` and real source URLs.
7. Confirm TGC performs a bounded second search round when initial evidence lacks territory scope.

## Gate B — Google / Gemini / ADK

1. Configure `GOOGLE_CLOUD_PROJECT`, location, model and application-default credentials.
2. Confirm `/api/runtime` reports `google_configured=true` and `adk_importable=true`.
3. Import `app.agent.root_agent` successfully.
4. Run a live case with open constraints.
5. Confirm Gemini returns bounded intervention JSON.
6. Confirm deterministic routing, not Gemini, chooses the final recommended world.

## Gate C — public deployment

1. Deploy exact tagged source candidate.
2. Open public HTTPS URL in a clean browser.
3. Run deterministic demo.
4. Run live partner/model demo.
5. Approve recommended world.
6. Confirm production revision increments and new PROOF cycle appears.
7. Verify health endpoint and runtime status.
8. Record the demo only after these checks pass.

## Stop conditions

Do not submit a claim of live integration if:

- Parallel calls fail or are mocked,
- Gemini/ADK cannot be invoked in the configured Google environment,
- the public URL depends on credentials judges will not have,
- authority skips re-verification,
- the video depicts behavior the public build cannot reproduce.
