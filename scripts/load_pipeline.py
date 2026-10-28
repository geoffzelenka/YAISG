"""Exercise real polling, realm reads and commodity inserts with httpx/asyncio.

Use disposable characters with market access, stock and free order slots. Tokens
come from YAISG_LOAD_TOKENS (a JSON array), never command-line arguments. Inserted
orders are cancelled and collected so each iteration returns their custody.
"""

import argparse
import asyncio
import json
import os
from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

import httpx


@dataclass
class Report:
    """Request latency samples and status totals for one workload."""

    latency_ms: list[float] = field(default_factory=list)
    statuses: Counter[str] = field(default_factory=Counter)
    failures: int = 0

    def summary(self, elapsed: float) -> dict[str, Any]:
        """Return JSON-safe throughput and latency percentiles."""
        ordered = sorted(self.latency_ms)
        return {
            "requests": len(ordered),
            "failures": self.failures,
            "seconds": round(elapsed, 3),
            "requests_per_second": round(len(ordered) / elapsed, 2),
            "p50_ms": round(ordered[len(ordered) // 2], 2) if ordered else 0,
            "p95_ms": round(ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))], 2)
            if ordered
            else 0,
            "statuses": dict(self.statuses),
        }


async def workload(
    client: httpx.AsyncClient,
    tokens: list[str],
    realm: str,
    item: str,
    workers: int,
    rounds: int,
) -> dict[str, Any]:
    """Run a bounded mixed workload and report every refusal or transport error."""
    report = Report()

    async def request(
        method: str, path: str, token: str, **kwargs: Any
    ) -> httpx.Response | None:
        started = perf_counter()
        try:
            response = await client.request(
                method, path, headers={"Authorization": f"Bearer {token}"}, **kwargs
            )
        except httpx.HTTPError:
            report.statuses["transport_error"] += 1
            report.failures += 1
            return None
        finally:
            report.latency_ms.append((perf_counter() - started) * 1000)
        report.statuses[str(response.status_code)] += 1
        if not response.is_success:
            report.failures += 1
        return response

    async def worker(index: int) -> None:
        token = tokens[index % len(tokens)]
        for _ in range(rounds):
            await request("GET", "/actions/poll", token)
            await request("GET", f"/realms/{realm}", token)
            created = await request(
                "POST",
                "/market/orders",
                token,
                json={"side": "sell", "item_id": item, "quantity": 1, "unit_price": 1},
            )
            if created is not None and created.is_success:
                identifier = created.json()["order"]["id"]
                await request("POST", f"/market/orders/{identifier}/cancel", token)
                await request("POST", f"/market/orders/{identifier}/collect", token)

    if not tokens or workers < 1 or rounds < 1:
        raise ValueError("Tokens, workers and rounds must be nonempty/positive")
    started = perf_counter()
    await asyncio.gather(*(worker(index) for index in range(workers)))
    return report.summary(perf_counter() - started)


async def main() -> None:
    """Run against an explicitly selected disposable deployment."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--realm", required=True)
    parser.add_argument("--item", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rounds", type=int, default=10)
    args = parser.parse_args()
    tokens = json.loads(os.environ["YAISG_LOAD_TOKENS"])
    if not isinstance(tokens, list) or not all(
        isinstance(t, str) and t for t in tokens
    ):
        raise ValueError("YAISG_LOAD_TOKENS must be a JSON array of bearer tokens")
    async with httpx.AsyncClient(base_url=args.base_url, timeout=30) as client:
        result = await workload(
            client, tokens, args.realm, args.item, args.workers, args.rounds
        )
    print(json.dumps(result, sort_keys=True))
    if result["failures"]:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
