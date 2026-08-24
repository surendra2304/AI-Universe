# AI UNIVERSE DIARY MAINTENANCE SPECIFICATION

**Document Version**: 1.0.0  
**Scope**: All current and future development, auditing, and maintenance of **AI Universe**.

---

## 1. Core Principles

1. **Chronological & Never-Ending**: The diary begins on **24 August 2026** and continues indefinitely.
2. **One detailed file per calendar day**: Each session must be logged in `diary/YYYY-MM-DD.md`.
3. **AI_UNIVERSE_DIARY.md**: The master consolidated index summarizing the project and linking to daily logs.
4. **Immutable historical days**: Past completed days are historical artifacts and must not be silently rewritten.
5. **Corrections to historical claims are ADDITIVE**: Use `## Corrections to Earlier Information` and explain previous claim, why it was wrong, evidence, and corrected state.
6. **Never fabricate**: Tests, API results, LLM provider outputs, Git commits, deployment status, or user interactions must be truthfully verified.
7. **Future work**: Must remain future work until actually completed.
8. **Zero Secrets**: Secrets NEVER belong in `AI_UNIVERSE_DIARY.md`, `diary/*.md`, `AI_UNIVERSE_DIARY_SPEC.md`, project memory, source code, tests, or Git. `.env` remains local-only.
9. **Bug Numbering**: Permanent global bug numbering (e.g., Bug #01). Never reuse, never delete. Additive corrections if fixed later.

---

## 2. File Organization

```text
/
├── AI_UNIVERSE_DIARY.md          # Master chronological index
├── AI_UNIVERSE_DIARY_SPEC.md     # This permanent maintenance specification
├── DIARY.md                      # Convenience link to master diary
├── diary/                        # Day-by-day detailed raw chronicle logs
│   ├── 2026-08-24.md
│   └── YYYY-MM-DD.md
├── scripts/
│   └── update_diary.py           # Diary scaffolding & sync automation
└── .agents/rules/
    └── diary_policy.md           # Agentic policy rule for diary maintenance
```

---

## 3. Standard Daily Entry Schema

Every daily entry in `diary/YYYY-MM-DD.md` must adhere to the following schema (omit irrelevant sections):

```markdown
# AI UNIVERSE — YYYY-MM-DD

## Daily Summary
## User Directives / Requirements
## Work Performed
## Architecture / Structure Changes
## Files Created
## Files Modified
## Files Deleted
## Multi-Provider / LLM Changes
## Agent Registry & Roles Changes
## Debate & Discussion Engine Changes
## Memory & Database Changes
## Evaluation & Benchmark Changes
## API & Router Changes
## CLI / UI Changes
## Security & Secret Guardrails
## Tests Performed & Test Results
## Bugs / Errors Discovered
### Bug #XX
- **Symptoms**:
- **Root Cause**:
- **Fix**:
- **Commit / PR**:
- **Verification**:
## Important Decisions
## Incidents / Misconfigurations
## Corrections to Earlier Information
## Git Commits
## API / Cloud Events
## Current End-of-Day State
## Next Planned Work
```
