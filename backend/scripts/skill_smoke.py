"""Smoke-check skill list endpoints against a running API.

Usage:
  python -m scripts.skill_smoke
  LOOM_API_URL=https://api.example.com LOOM_API_TOKEN=... python -m scripts.skill_smoke
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

import httpx

SLUGS = (
    "glossary",
    "citations",
    "deadlines",
    "contradictions",
    "reading",
    "products",
    "jobs",
    "contract-flags",
    "form-filler/profiles",
    "form-filler/documents",
    "live-doc-diff/sets",
    "auto-attach/documents",
)


async def main_async(base: str, token: str) -> int:
    headers = {"Authorization": f"Bearer {token}"}
    failed: list[str] = []
    async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=20.0) as client:
        health = await client.get("/health")
        print(f"GET /health -> {health.status_code}")
        if health.status_code != 200:
            print("API health check failed; aborting.")
            return 1

        for path in ("/api/overview", "/api/digest", "/api/trail", "/api/notifications", "/api/briefs"):
            response = await client.get(path, headers=headers)
            line = f"GET {path} -> {response.status_code}"
            print(line)
            if response.status_code >= 400:
                failed.append(line)

        ask = await client.post(
            "/api/ask",
            headers=headers,
            json={"question": "What did I save recently?"},
        )
        print(f"POST /api/ask -> {ask.status_code}")
        if ask.status_code >= 400:
            failed.append(f"POST /api/ask -> {ask.status_code}")

        for slug in SLUGS:
            path = f"/api/skills/{slug}"
            response = await client.get(path, headers=headers, params={"limit": 5})
            line = f"GET {path} -> {response.status_code}"
            print(line)
            if response.status_code >= 400:
                failed.append(line)

    if failed:
        print("\nFailures:")
        for line in failed:
            print(f"  - {line}")
        return 1
    print("\nAll smoke checks passed.")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        default=os.environ.get("LOOM_API_URL", "http://127.0.0.1:8000"),
    )
    parser.add_argument(
        "--token",
        default=os.environ.get("LOOM_API_TOKEN", "loom-dev-token"),
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main_async(args.base, args.token)))


if __name__ == "__main__":
    main()
