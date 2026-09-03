from __future__ import annotations

import re
from dataclasses import dataclass

_PATTERNS = [
    re.compile(r"ignore (?:all|any) previous instructions", re.I),
    re.compile(r"reveal (?:the )?(?:system|developer) prompt", re.I),
    re.compile(r"exfiltrat|steal.{0,40}(?:key|token|secret)", re.I),
]


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    sanitized: str
    findings: tuple[str, ...]


def inspect(text: str) -> GuardResult:
    findings = []
    for p in _PATTERNS:
        if p.search(text):
            findings.append(p.pattern)
    sanitized = re.sub(r"(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,})", "[REDACTED]", text)
    return GuardResult(not findings, sanitized, tuple(findings))


def guard_messages(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        c = m.get("content", "")
        if isinstance(c, str):
            result = inspect(c)
            out.append({**m, "content": result.sanitized})
        else:
            out.append(m)
    return out
