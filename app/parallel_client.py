from __future__ import annotations

import os
from typing import Any
import httpx


class ParallelSearchError(RuntimeError):
    pass


class ParallelSearchClient:
    """Narrow runtime adapter for Parallel Search.

    Defaults follow Parallel's current Search API surface while allowing hackathon
    environment overrides. Fresh web information enters through this single auditable
    boundary and is normalized before it can influence the decision engine.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key or os.getenv("PARALLEL_API_KEY", "")
        self.base_url = base_url or os.getenv("PARALLEL_SEARCH_URL", "https://api.parallel.ai/v1beta/search")
        self.beta_header = os.getenv("PARALLEL_BETA_HEADER", "search-extract-2025-10-10")

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        objective: str,
        search_queries: list[str],
        *,
        max_results: int = 8,
        max_chars_per_result: int = 5000,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise ParallelSearchError("PARALLEL_API_KEY is not configured")
        queries = [q.strip() for q in search_queries if q and q.strip()][:4]
        if not queries:
            raise ParallelSearchError("At least one search query is required")
        payload = {
            "objective": objective.strip(),
            "search_queries": queries,
            "max_results": max(1, min(20, int(max_results))),
            "max_chars_per_result": max(500, min(10000, int(max_chars_per_result))),
        }
        headers = {"Content-Type": "application/json", "x-api-key": self.api_key}
        if "v1beta" in self.base_url and self.beta_header:
            headers["parallel-beta"] = self.beta_header

        async with httpx.AsyncClient(timeout=35.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise ParallelSearchError(f"Parallel Search failed: HTTP {response.status_code}: {response.text[:700]}")
        data = response.json()
        if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
            raise ParallelSearchError("Parallel Search returned an unexpected response shape")
        return data
