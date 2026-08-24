# REST API Specification

## Endpoints Summary

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | `GET` | Service liveness, provider readiness & database health |
| `/agents` | `GET` | List registered specialist agents and capabilities |
| `/ask` | `POST` | Execute question answering through task router (Fast/Review/Debate) |
| `/debate` | `POST` | Explicitly trigger multi-agent structured debate |
| `/tasks/{id}` | `GET` | Query task status and execution state |
| `/runs/{id}` | `GET` | Retrieve full audit trail, round transcripts, and agent contributions |
| `/memory/search`| `POST` | Search agent or system memory with scope checks |
| `/experiments` | `POST` | Launch comparative model/strategy experiment |
| `/experiments/{id}`| `GET` | Fetch experiment results and metrics |
| `/strategies` | `GET` | Inspect learned routing strategies |
