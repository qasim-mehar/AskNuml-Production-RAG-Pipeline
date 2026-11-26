"""ADR 0011: persistence gates the real papers provider (L5, L12).

The contract runs against Lane D's real Postgres adapter on an in-memory SQLite
engine with Alembic at head, then through the API-local provider and route. No
Docker, live site or paid provider is involved.
"""

from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from tests.contracts.parsed_record_contract import assert_parsed_record_roundtrip_contract
from uni_rag_api.app import create_app
from uni_rag_api.composition import Backend, ephemeral_settings, seeded_fake_object_store
from uni_rag_api.fixtures import LAST_CRAWLED, PAPER_RECORDS
from uni_rag_api.service import seed_paper_records
from uni_rag_core import ApiSection, FakeClock
from uni_rag_indexing.adapters.postgres_metadata_store import PostgresMetadataStore

MIGRATIONS = Path(__file__).resolve().parents[2] / "infra" / "migrations"


@pytest.fixture
def migrated_store() -> Iterator[PostgresMetadataStore]:
    """A real adapter over a migrated in-memory database, reverted after each test."""
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    config = Config(str(MIGRATIONS / "alembic.ini"))
    config.set_main_option("script_location", str(MIGRATIONS))
    config.set_main_option("sqlalchemy.url", "sqlite://")
    config.attributes["engine"] = engine
    command.upgrade(config, "head")
    try:
        yield PostgresMetadataStore(engine, clock=FakeClock(LAST_CRAWLED))
    finally:
        command.downgrade(config, "base")
        engine.dispose()


def test_persisted_paper_record_round_trips_with_frozen_provenance(
    migrated_store: PostgresMetadataStore,
) -> None:
    """The ADR's stated rule: stored provenance survives find() unchanged."""
    assert_parsed_record_roundtrip_contract(
        migrated_store, PAPER_RECORDS[0], object_store=seeded_fake_object_store()
    )


def test_persisted_records_are_served_verbatim_by_the_real_provider(
    migrated_store: PostgresMetadataStore,
) -> None:
    """The HTTP boundary adds no fixture fallback: the store alone feeds results."""
    settings = ephemeral_settings(api=ApiSection(rate_limit_capacity=1000))
    app = create_app(
        settings,
        clock=FakeClock(LAST_CRAWLED),
        backend=Backend.REAL,
        paper_record_store=migrated_store,
        object_store=seeded_fake_object_store(),
    )

    with TestClient(app) as client:
        assert app.state.paper_record_store is migrated_store
        empty = client.get("/api/v1/papers")
        assert empty.status_code == 200
        assert empty.json() == {"results": []}

        seed_paper_records(
            migrated_store, PAPER_RECORDS, indexed_at=LAST_CRAWLED + timedelta(days=1)
        )
        response = client.get("/api/v1/papers")
        image = response.json()["results"][0]["image_ref"]
        image_response = client.get(image["image_url"])

    assert response.status_code == 200
    assert response.json() == {
        "results": [record.model_dump(mode="json") for record in PAPER_RECORDS]
    }
    assert PAPER_RECORDS[0].image_ref is not None
    assert image["ref_id"] == PAPER_RECORDS[0].image_ref.ref_id
    assert image_response.status_code == 200
