"""Measure query latency against the fake backend only (L1).

Run with ``uv run python apps/api/scripts/benchmark.py --requests 200``. The
logged record is explicitly labelled ``backend=fake``; these numbers are not
production capacity estimates.
"""

import argparse
from math import ceil
from time import perf_counter

from fastapi.testclient import TestClient

from uni_rag_api.app import create_app
from uni_rag_api.config import ApiSettings
from uni_rag_api.fixtures import QUERY_EN
from uni_rag_core import Language, configure_logging, get_logger


def percentile(values: list[float], fraction: float) -> float:
    """Return the nearest-rank percentile of ``values`` in milliseconds."""
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(fraction * len(ordered)) - 1))
    return round(ordered[index], 3)


def main() -> None:
    """Run the in-process fake-backed load and log a labelled latency summary."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=200)
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be at least 1")

    configure_logging("INFO")
    settings = ApiSettings(auth_enabled=False, rate_limit_capacity=args.requests + 10)
    with TestClient(create_app(settings)) as client:
        latencies: list[float] = []
        for _ in range(args.requests):
            started = perf_counter()
            response = client.post(
                "/api/v1/query",
                json={
                    "query_id": "query-benchmark-001",
                    "text": QUERY_EN,
                    "language": Language.EN.value,
                    "top_k": 5,
                    "filters": {},
                },
            )
            latencies.append((perf_counter() - started) * 1000)
            if response.status_code != 200:
                msg = f"benchmark request failed with status {response.status_code}"
                raise RuntimeError(msg)

    get_logger("uni_rag_api.benchmark").info(
        "api.benchmark",
        backend="fake",
        load={
            "requests": args.requests,
            "concurrency": 1,
            "endpoint": "/api/v1/query",
            "transport": "in-process TestClient",
        },
        latency_ms={
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": round(max(latencies), 3),
        },
        note="fake-backend measurement only; not production capacity",
    )


if __name__ == "__main__":
    main()
