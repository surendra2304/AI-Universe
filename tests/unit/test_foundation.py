"""Unit tests for configuration, logging, ID utilities, and health endpoint."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.utils.ids import (
    generate_debate_id,
    generate_deterministic_id,
    generate_message_id,
    generate_run_id,
    generate_task_id,
)
from app.utils.logger import setup_logger


def test_settings_initialization():
    """Verify Settings class loads correct defaults and types."""
    test_settings = Settings()
    assert test_settings.APP_NAME == "Inference"
    assert test_settings.DATABASE_URL == "sqlite:///data/universe.db"
    assert test_settings.MAX_BUDGET == 999999.0
    assert test_settings.REQUEST_TIMEOUT == 60.0


def test_id_generators():
    """Verify ID generation prefixing, uniqueness, and reproducibility."""
    task_id1 = generate_task_id()
    task_id2 = generate_task_id()
    assert task_id1.startswith("task_")
    assert task_id1 != task_id2

    run_id = generate_run_id()
    assert run_id.startswith("run_")

    debate_id = generate_debate_id()
    assert debate_id.startswith("deb_")

    msg_id = generate_message_id()
    assert msg_id.startswith("msg_")

    det_id1 = generate_deterministic_id("task", "fixed_input")
    det_id2 = generate_deterministic_id("task", "fixed_input")
    assert det_id1 == det_id2
    assert det_id1.startswith("task_")


def test_logger_setup():
    """Verify logger configuration and level setup."""
    custom_logger = setup_logger("test_logger", log_level="DEBUG")
    assert custom_logger.name == "test_logger"
    assert len(custom_logger.handlers) > 0


def test_health_endpoint():
    """Verify FastAPI /health endpoint returns expected response."""
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data

