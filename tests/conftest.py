"""Pytest fixtures and configuration for AI Universe test suite."""

import pytest
from app.core.config import settings


@pytest.fixture(autouse=True)
def mock_all_provider_api_keys(monkeypatch):
    """Ensure all active provider API keys are populated during tests."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "mock_gemini_key_123")
    monkeypatch.setattr(settings, "GROQ_API_KEY", "mock_groq_key_123")
    monkeypatch.setattr(settings, "MISTRAL_API_KEY", "mock_mistral_key_123")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "mock_openrouter_key_123")
    monkeypatch.setattr(settings, "COHERE_API_KEY", "mock_cohere_key_123")
    monkeypatch.setattr(settings, "HUGGINGFACE_API_KEY", "mock_huggingface_key_123")
    monkeypatch.setattr(settings, "CLOUDFLARE_API_KEY", "mock_cloudflare_key_123")
    monkeypatch.setattr(settings, "CLOUDFLARE_ACCOUNT_ID", "mock_cloudflare_acc_123")
    monkeypatch.setattr(settings, "NVIDIA_API_KEY", "mock_nvidia_key_123")
    monkeypatch.setattr(settings, "FRIDAY_API_KEY", "test_friday_secret_key_12345")
