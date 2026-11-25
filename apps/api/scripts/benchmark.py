"""Measure /api/v1/query and /api/v1/papers latency on both backends (L1).

Run with ``uv run python apps/api/scripts/benchmark.py --requests 200 --backend fake``
(or ``--backend real`` for the pipeline composed with deterministic fakes).
Records are labelled with the backend and load; the papers route stays
fixture-backed on both backends until parsed-record persistence is promoted.
These are in-process numbers, not production capacity estimates.
"""

import argparse
from math import ceil
from time import perf_counter

from fastapi.testclient import TestClient
from httpx import Response

from uni_rag_api.app import create_app
from uni_rag_api.composition import Backend, ephemeral_settings, seeded_pipeline_ports
from uni_rag_api.fixtures import PAPER_RECORDS, QUERY_EN
from uni_rag_core import ApiSection, Language, configure_logging, get_logger


def percentile(values: list[float], fraction: float) -> float:
    """Return the nearest-rank percentile of ``values`` in milliseconds."""
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, ceil(fraction * len(ordered)) - 1))
    return round(ordered[index], 3)


def _summary(values: list[float]) -> dict[str, float]:
    """Summarise in-process latencies without hiding the worst case."""
    return {
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
        "max": round(max(values), 3),
    }


def _check(response: Response, label: str) -> None:
    """Fail loudly if a measured request did not succeed (L1)."""
    if response.status_code != 200:
        msg = f"{label} benchmark request failed with status {response.status_code}"
        raise RuntimeError(msg)


def main() -> None:
    """Run labelled in-process load and log latency percentiles per backend."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--backend", type=Backend, choices=list(Backend), default=Backend.FAKE)
    args = parser.parse_args()
    if args.requests < 1:
        parser.error("--requests must be at least 1")

    configure_logging("INFO")
    settings = ephemeral_settings(api=ApiSection(rate_limit_capacity=args.requests * 2 + 10))
    app = create_app(
        settings,
        backend=args.backend,
        pipeline_ports=seeded_pipeline_ports() if args.backend is Backend.REAL else None,
    )
    paper = PAPER_RECORDS[0]
    with TestClient(app) as client:
        query_latencies: list[float] = []
        papers_latencies: list[float] = []
        for _ in range(args.requests):
            started = perf_counter()
            query_response = client.post(
                "/api/v1/query",
                json={
                    "query_id": "query-benchmark-001",
                    "text": QUERY_EN,
                    "language": Language.EN.value,
                    "top_k": 5,
                    "filters": {},
                },
            )
            query_latencies.append((perf_counter() - started) * 1000)
            _check(query_response, "/api/v1/query")

            started = perf_counter()
            papers_response = client.get(
                "/api/v1/papers",
                params={
                    "course_code": paper.course_code,
                    "year": paper.year,
                    "term": paper.term,
                    "exam_type": paper.exam_type,
                },
            )
            papers_latencies.append((perf_counter() - started) * 1000)
            _check(papers_response, "/api/v1/papers")

    get_logger("uni_rag_api.benchmark").info(
        "api.benchmark",
        backend=args.backend.value,
        load={
            "requests_per_endpoint": args.requests,
            "endpoints": ["/api/v1/query", "/api/v1/papers"],
            "concurrency": 1,
            "transport": "in-process TestClient",
        },
        papers_data={
            "source": "fake",
            "label": "fixture-backed route; parsed-record persistence parked",
        },
        latency_ms={
            "/api/v1/query": _summary(query_latencies),
            "/api/v1/papers": _summary(papers_latencies),
        },
        note="in-process measurement only; not production capacity",
    )


if __name__ == "__main__":
    main()
