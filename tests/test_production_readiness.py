"""Production Readiness and Security Hardening Test Suite."""

from fastapi.testclient import TestClient

from app.ha.high_availability import ha_manager
from app.main import app
from app.observability_system import observability_collector
from app.performance_cache import perf_cache
from app.security.api_security import security_manager

client = TestClient(app)


def test_security_headers_present():
    """Verifies that all required production security headers are set in HTTP responses."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "1; mode=block"
    assert "Strict-Transport-Security" in resp.headers


def test_api_key_validation():
    """Tests bearer key validation logic."""
    assert security_manager.validate_api_key("aiu_live_sec_9948271049281726") is True
    assert security_manager.validate_api_key("Bearer aiu_live_sec_9948271049281726") is True
    assert security_manager.validate_api_key("invalid_fake_key") is False
    assert security_manager.validate_api_key(None) is False


def test_input_sanitization():
    """Tests malicious input removal."""
    dirty = "SELECT * FROM users; <script>alert(1)</script> DROP TABLE logs; --"
    clean = security_manager.sanitize_input(dirty)
    assert "<script>" not in clean
    assert "DROP TABLE" not in clean
    assert "--" not in clean


def test_multi_level_cache_and_ttl():
    """Tests caching and statistics."""
    perf_cache.clear()
    perf_cache.set("test_key", {"data": 123})
    assert perf_cache.get("test_key") == {"data": 123}
    assert perf_cache.get("non_existent_key") is None

    stats = perf_cache.get_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_high_availability_failover():
    """Tests provider failover and degradation marking."""
    chain = ha_manager.get_healthy_provider_chain()
    assert len(chain) >= 4

    # Simulate 3 failures for primary
    ha_manager.record_provider_result("groq", success=False)
    ha_manager.record_provider_result("groq", success=False)
    ha_manager.record_provider_result("groq", success=False)

    status = ha_manager.get_ha_status()
    assert status["ha_mode"] == "ACTIVE_REDUNDANT"

    # Reset health
    ha_manager.record_provider_result("groq", success=True)
    assert ha_manager.provider_health["groq"]["status"] == "HEALTHY"


def test_observability_snapshot():
    """Tests observability metrics collection."""
    observability_collector.record_request(0.05, is_error=False)
    snap = observability_collector.get_observability_snapshot()
    assert snap["total_requests"] >= 1
    assert "business_metrics" in snap
