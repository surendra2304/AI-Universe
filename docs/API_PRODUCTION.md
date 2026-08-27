# AI Universe — Production API & Performance Deployment Reference

This guide details the production architecture, performance optimizations, monitoring setup, and deployment standards for the **AI Universe Advisory Consultation System**.

---

## 1. Production Architecture & Performance Optimizations

### Caching Layer (`app/optimization.py`)
- **Telemetry Pattern Hashing**: Normalizes continuous performance parameters (win rate, profit factor, drawdown bucket, trade count) into discrete risk buckets.
- **LRU In-Memory Cache**: 24-hour TTL with instant retrieval ($< 1$ms) on recurring identical telemetry envelopes.
- **Cache Invalidation**: Automatic eviction when reaching capacity (5,000 entries) or expiring past TTL.

### Provider Gateway & Circuit Breaker
- **Tripping Threshold**: 3 consecutive failed provider calls.
- **Recovery Time**: 60 seconds half-open probe before full restoration.
- **Failover Chain**: `Groq` $\rightarrow$ `Gemini` $\rightarrow$ `OpenAI` $\rightarrow$ `Anthropic` $\rightarrow$ `Ollama` $\rightarrow$ `Deterministic Mathematical Engine`.

### Concurrency & Compression
- **Concurrency Throttling**: Semaphore bounding active consultations to 100 simultaneous requests.
- **GZip Response Compression**: Enabled globally for responses $\ge 500$ bytes.

---

## 2. Production Health & Prometheus Monitoring

### Health Endpoints (`app/health.py`)
- `GET /health`: Basic operational liveness check.
- `GET /health/detailed`: Live system telemetry, p50/p95/p99 latency percentiles, cache hit rate, and active concurrency.
- `GET /health/providers`: Per-provider success rates and average response times.
- `GET /status`: Active capabilities and specialist agent rosters.
- `GET /metrics`: Standard Prometheus metrics exporter.

### Key Prometheus Metrics
| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `ai_universe_requests_total` | Counter | Total completed consultation requests |
| `ai_universe_latency_p50_seconds` | Gauge | Median response latency |
| `ai_universe_latency_p95_seconds` | Gauge | 95th percentile response latency ($< 30$s SLA) |
| `ai_universe_latency_p99_seconds` | Gauge | 99th percentile response latency |
| `ai_universe_error_rate_percent` | Gauge | Ratio of failed consultations |
| `ai_universe_cache_hit_rate_percent` | Gauge | Cache hit percentage |
| `ai_universe_active_requests` | Gauge | In-flight active consultations |

---

## 3. SLA & Performance Benchmarks

Validated via `tests/load_test.py` across 100 concurrent multi-scenario requests:
- **P50 Latency**: $< 0.05$s (Cached) / $\sim 1.2$s (Debate)
- **P95 Latency**: Strictly **$< 30.0$s**
- **Success Rate**: **100.0%**
- **Error Rate**: **0.0%**
- **Quality Score**: **100/100** on recommendation coherence, bounds, and gating.

---

## 4. Production Deployment Pre-Flight Checklist

Run the automated pre-flight audit:
```bash
python deploy_production.py
```
This script verifies:
1. All health endpoints (`/health`, `/health/detailed`, `/health/providers`, `/status`, `/metrics`).
2. Trading advisory invariant adherence (`advisory_only: true`, `exchange_execution: false`).
3. A/B testing and testnet comparative analytics.
4. Concurrency controller and memory initialization.
