from app.inference_runtime.key_pool import SafeKeyPool


def test_all_quarantined_fails_closed():
    p = SafeKeyPool("x", ["a", "b"])
    p.quarantine("a", 100)
    p.quarantine("b", 100)
    assert p.choose() is None


def test_rotation_skips_quarantined():
    p = SafeKeyPool("x", ["a", "b"])
    p.quarantine("a", 100)
    assert p.choose() == "b"


def test_replace_resets():
    p = SafeKeyPool("x", ["a"])
    p.quarantine("a", 100)
    p.replace(["b"])
    assert p.choose() == "b"


def test_delay_positive_when_quarantined():
    p = SafeKeyPool("x", ["a"])
    p.quarantine("a", 10)
    assert p.next_available_delay() > 0
