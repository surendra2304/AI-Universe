# Inference Permanent Project Memory Rule: Diary Maintenance

## Core Architecture
- **Master Index**: `inference_DIARY.md` (Concise consolidated chronological history with links to all daily files)
- **Daily Raw Chronicles**: `diary/YYYY-MM-DD.md` (Detailed single file per calendar day)
- **Specification Standard**: `inference_DIARY_SPEC.md`
- **Automation Helper**: `scripts/update_diary.py`

## Permanent Requirement
Every meaningful completed engineering task MUST update the diary automatically. This is NOT an optional step.

### Mandatory Workflow
1. **BEFORE TASK**:
   - Read the current diary state and `inference_DIARY_SPEC.md`.
   - Determine today's actual calendar date (e.g. `2026-08-24`).
   - Inspect relevant historical context.

2. **DURING TASK**:
   Track and record:
   - User requirements and directives
   - Work performed and architectural choices
   - Files created, modified, or deleted
   - Provider gateway & agent modifications
   - Debate engine & memory subsystem evolution
   - Bugs discovered, symptoms, root causes, and fixes (with global Bug # numbering)
   - Important engineering decisions
   - Automated and manual test results
   - Security verifications
   - Git commits and push state
   - Known limitations and current end-of-day state

3. **AFTER TASK**:
   - Update today's `diary/YYYY-MM-DD.md` using the standard schema.
   - Update `inference_DIARY.md` master index summary.
   - Verify that no secrets, API keys, tokens, passwords, or `.env` entries exist in the diary.
   - Stage and commit the diary alongside code changes.

### Date & File Rules
- **One File Per Calendar Day**: Exactly one `diary/YYYY-MM-DD.md` per date. Never create duplicate files for the same date. Never invent dates.
- **Master Index Synchronization**: `inference_DIARY.md` must list every daily file chronologically starting from project inception (**2026-08-24**).

### History & Additive Corrections Rule
- Completed historical daily entries are immutable records of project evolution.
- If an earlier claim or assumption is discovered to be inaccurate, **DO NOT silently rewrite historical files**.
- Record an explicit additive correction in today's entry under `## Corrections to Earlier Information`.

### Security Gate
- **Zero Secrets**: Never store API keys, tokens, passwords, private keys, or `.env` contents in `inference_DIARY.md`, `diary/*.md`, or any repository file.
