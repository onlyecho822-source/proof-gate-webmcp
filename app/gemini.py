from __future__ import annotations

import json
import os
from typing import Any


class GeminiRuntimeError(RuntimeError):
    pass


def google_configured() -> bool:
    return bool(os.getenv("GOOGLE_CLOUD_PROJECT"))


async def generate_interventions_with_gemini(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Use Gemini on Vertex AI for bounded COUNTERFACTUAL proposals.

    Gemini is a proposal generator here, not the decision authority. Deterministic code
    propagates the consequences, compares worlds, selects the minimum useful action,
    and keeps creative mutation behind AUTHORITY.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    if not project:
        raise GeminiRuntimeError("GOOGLE_CLOUD_PROJECT is not configured")
    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise GeminiRuntimeError(f"google-genai import failed: {exc}") from exc

    client = genai.Client(vertexai=True, project=project, location=location)
    prompt = f"""
You are COUNTERFACTUAL mode inside a governed media-production decision system.
Given the JSON context below, propose up to THREE interventions PER BLOCKED ASSET,
with no more than nine interventions total.

Rules:
- Do not make legal conclusions or claim clearance.
- Prefer reversible, production-realistic changes.
- Use only asset_id and constraint IDs present in context.
- Every creative mutation requires human approval.
- Do not score or choose the winner; the deterministic engine does that.

Return JSON only as an array. Each item must contain:
asset_id, action, description, estimated_cost, delay_hours,
creative_disruption (0-10), rights_uncertainty (0-10), irreversibility (0-10),
clears_constraints (array of exact IDs), requires_human_approval.

CONTEXT:
{json.dumps(context, ensure_ascii=False)[:24000]}
"""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.2,
            response_mime_type="application/json",
            max_output_tokens=4200,
        ),
    )
    text = getattr(response, "text", "") or ""
    try:
        data = json.loads(text)
    except Exception as exc:
        raise GeminiRuntimeError(f"Gemini returned invalid JSON: {text[:700]}") from exc
    if not isinstance(data, list):
        raise GeminiRuntimeError("Gemini intervention output must be a JSON array")
    return data[:9]
