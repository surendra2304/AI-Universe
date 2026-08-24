"""Foundation tests for AI Universe project setup."""

from app.core.config import Settings
from app.main import app
from fastapi.testclient import TestClient


def test_settings_initialization():
    settings = Settings()
    assert settings.APP_NAME == "AI Universe"
    assert "sqlite" in settings.DATABASE_URL


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
