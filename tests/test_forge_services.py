"""Tests for FORGE-supporting Intelligence Services."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routing.consumer_router import consumer_router

client = TestClient(app)


def test_forge_code_generation_endpoint():
    """Tests POST /v1/forge/generate-code."""
    payload = {
        "file_type": "python",
        "filename": "app/calculator.py",
        "context": {"project_goal": "A robust financial calculator"},
        "requirements": ["Function to compute Sharpe ratio", "Full type annotations and docstrings"],
        "language_features": ["type hints", "PEP 8"]
    }
    resp = client.post("/v1/forge/generate-code", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data
    assert data["filename"] == "app/calculator.py"
    assert data["confidence"] > 0.5


def test_forge_architecture_planning_endpoint():
    """Tests POST /v1/forge/plan-architecture."""
    payload = {
        "goal": "Build a real-time portfolio analytics dashboard",
        "project_type": "api",
        "constraints": ["FastAPI", "Low latency"],
        "preferences": ["AsyncIO", "Pydantic v2"]
    }
    resp = client.post("/v1/forge/plan-architecture", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "architecture_spec" in data
    assert len(data["file_manifest"]) >= 3
    assert len(data["tech_stack"]) >= 1


def test_forge_code_review_endpoint():
    """Tests POST /v1/forge/review-code."""
    clean_code = "def add(a: int, b: int) -> int:\n    \"\"\"Add numbers.\"\"\"\n    return a + b\n"
    payload = {
        "code": clean_code,
        "filename": "math_ops.py",
        "project_context": "Core math utilities",
        "review_focus": ["bugs", "security"]
    }
    resp = client.post("/v1/forge/review-code", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["verdict"] in ("approve", "needs_review", "fix_required")
    assert "debate_summary" in data


def test_forge_debugging_endpoint():
    """Tests POST /v1/forge/debug."""
    payload = {
        "error": "ZeroDivisionError: division by zero",
        "traceback": "Traceback (most recent call last):\n  File 'calc.py', line 10, in div\n    return a / b",
        "code_context": "def div(a, b):\n    return a / b",
        "attempted_fixes": ["return a // b"],
        "verification_failure": "assert div(10, 0) == 0"
    }
    resp = client.post("/v1/forge/debug", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "root_cause" in data
    assert "fix_strategy" in data


def test_forge_test_generation_endpoint():
    """Tests POST /v1/forge/generate-tests."""
    payload = {
        "code": "def multiply(x: float, y: float) -> float:\n    return x * y",
        "file_type": "python",
        "test_framework": "pytest",
        "coverage_targets": ["multiply positive", "multiply zero", "multiply negative"]
    }
    resp = client.post("/v1/forge/generate-tests", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "test_code" in data
    assert data["coverage_estimate"] >= 0.8


def test_forge_batch_generate_endpoint():
    """Tests POST /v1/forge/batch-generate with multiple files."""
    payload = {
        "requests": [
            {
                "file_type": "python",
                "filename": "app/models.py",
                "requirements": ["Pydantic model for User"]
            },
            {
                "file_type": "html",
                "filename": "index.html",
                "requirements": ["Semantic HTML5 landing page"]
            }
        ]
    }
    resp = client.post("/v1/forge/batch-generate", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    assert data["total_tokens"] > 0


def test_forge_health_and_capabilities_endpoints():
    """Tests GET /v1/forge/health, /capabilities, and admin usage."""
    resp_h = client.get("/v1/forge/health")
    assert resp_h.status_code == 200
    assert resp_h.json()["status"] in ("healthy", "degraded")

    resp_c = client.get("/v1/forge/capabilities")
    assert resp_c.status_code == 200
    assert len(resp_c.json()["services"]) >= 5

    resp_u = client.get("/v1/admin/usage?consumer=forge")
    assert resp_u.status_code == 200
    assert "total_calls" in resp_u.json()
