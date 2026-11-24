"""Every schema round-trips through JSON without loss."""

import pytest
from pydantic import BaseModel

from tests.factories import all_models


@pytest.mark.parametrize("model", all_models(), ids=lambda model: type(model).__name__)
def test_schema_json_roundtrip(model: BaseModel) -> None:
    encoded = model.model_dump_json()
    decoded = type(model).model_validate_json(encoded)
    assert decoded == model
    assert decoded.model_dump_json() == encoded
