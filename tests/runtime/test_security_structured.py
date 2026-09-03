import pytest

from app.inference_runtime.errors import SchemaViolation
from app.inference_runtime.security import constant_time_equal, redact
from app.inference_runtime.structured import validate_json


def test_secret_redaction():
    assert "[REDACTED]" in redact("Authorization: Bearer abcdefghijklmnop").text


def test_constant_time_compare():
    assert constant_time_equal("a", "a") and not constant_time_equal("a", "b")


def test_json_schema():
    assert (
        validate_json('{"x":2}', {"type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}})["x"]
        == 2
    )


def test_json_schema_rejects_bad_type():
    with pytest.raises(SchemaViolation):
        validate_json('{"x":"2"}', {"type": "object", "required": ["x"], "properties": {"x": {"type": "integer"}}})
