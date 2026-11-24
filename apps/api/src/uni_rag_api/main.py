"""FastAPI application entry point for the uni-rag API."""

from fastapi import FastAPI

app = FastAPI(title="uni-rag API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok", "service": "uni-rag-api"}


@app.get("/ready")
def ready() -> dict[str, str]:
    """Readiness probe."""
    return {"status": "ready"}
