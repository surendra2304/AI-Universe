# Trading Consultation & A/B Testing API Reference

The **Trading Consultation API** exposes AI Universe as an asynchronous advisory intelligence layer for autonomous trading bots. It provides multi-agent deliberation over quantitative performance metrics, parameter adjustments, drawdown risk assessments, and **A/B experimental arm evaluations (Control vs. Treatment)**.

> [!IMPORTANT]
> **Safety Rule & Invariant**: AI Universe is strictly an **advisory system**. It never interacts with exchange endpoints, never holds or signs private keys, and never executes trades. Trading bots independently validate all returned parameter recommendations against hard deterministic safety bounds.

---

## Architecture Overview

When a trading bot submits performance telemetry, AI Universe convenes a dedicated multi-agent specialist panel:
1. **Trading Analyst (`trading_analyst`)**: Analyzes win rate, profit factor, drawdown curves, and consecutive loss streaks to propose initial parameter calibrations.
2. **Strategist (`strategist`)**: Evaluates trade-offs between capital preservation and trade frequency across active strategies and ensures A/B treatment arms do not diverge excessively from control baselines.
3. **Adversarial Critic (`critic`)**: Challenges curve-fitting risks, small-sample overfitting, and regime shifts.
4. **Data Analyst (`data_analyst`)**: Quantitatively verifies empirical distributions, mathematical significance thresholds, and cross-arm delta statistics.
5. **Synthesizer (`synthesizer`)**: Emits a bounded `AIUniverseDecision` respecting hard constraints.

### Synthesis Decision Rules
- **Maximum 2 parameter adjustments** per decision (prefers 1).
- **Mandatory Quantitative Evidence**: Every adjustment must cite specific telemetry metrics (e.g. *"consecutive_losses=6 justifies tightening stop_loss_pct by 15%"*).
- **Sample Size Gate**: If total closed trades $N < 20$, the system strictly returns `status = "INSUFFICIENT_DATA"`.
- **Healthy Gate**: If win rate $\ge 50\%$, profit factor $\ge 1.25$, and max drawdown $\le 5\%$, the system returns `status = "NO_CHANGE"`.
- **A/B Testing Control Bound**: When consulting for a `TREATMENT` arm with `control_metrics`, adjustments are bounded conservatively ($\le \pm 15\%$) to preserve comparative experimental validity while generating a `comparison_rationale` and `expected_improvement`.

---

## A/B Testing Endpoints

### 1. Register & Start A/B Experiment
`POST /v1/trading/experiment/start`

Initializes a new A/B experiment comparing a CONTROL baseline arm against a TREATMENT calibration arm.

#### Request Payload (`ExperimentStartRequest`)
```json
{
  "experiment_id": "exp_volatility_v2",
  "hypothesis": "Tighter trailing stop losses reduce drawdown in choppy volatility without degrading profit factor.",
  "duration_hours": 48.0,
  "success_metrics": ["profit_factor", "max_drawdown_pct", "win_rate"],
  "control_bot_id": "bot_ctrl_01",
  "treatment_bot_id": "bot_treat_01",
  "initial_parameters": {
    "Supertrend_5m": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.03
    }
  }
}
```

#### Response Payload (`ExperimentConfigResponse`)
```json
{
  "experiment_id": "exp_volatility_v2",
  "status": "ACTIVE",
  "start_time": "2026-08-27T16:00:00.000000",
  "duration_hours": 48.0,
  "control_config": {
    "bot_id": "bot_ctrl_01",
    "arm": "CONTROL",
    "parameters": {"Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}}
  },
  "treatment_config": {
    "bot_id": "bot_treat_01",
    "arm": "TREATMENT",
    "parameters": {"Supertrend_5m": {"stop_loss_pct": 0.02, "take_profit_pct": 0.03}}
  },
  "success_metrics": ["profit_factor", "max_drawdown_pct", "win_rate"],
  "message": "A/B Experiment successfully initialized."
}
```

---

### 2. Check Experiment Status
`GET /v1/trading/experiment/{experiment_id}/status`

#### Response Payload (`ExperimentStatusResponse`)
```json
{
  "experiment_id": "exp_volatility_v2",
  "status": "ACTIVE",
  "start_time": "2026-08-27T16:00:00.000000",
  "elapsed_hours": 12.5,
  "duration_hours": 48.0,
  "active_arms": ["bot_ctrl_01", "bot_treat_01"],
  "consultations_count": {
    "CONTROL": 3,
    "TREATMENT": 3
  },
  "latest_telemetry": { ... }
}
```

---

### 3. Retrieve Experiment Comparative Results
`GET /v1/trading/experiment/{experiment_id}/results`

#### Response Payload (`ExperimentResultsResponse`)
```json
{
  "experiment_id": "exp_volatility_v2",
  "status": "COMPLETED",
  "winner": "TREATMENT",
  "duration_hours": 48.0,
  "control_summary": {
    "bot_id": "bot_ctrl_01",
    "total_trades": 52,
    "win_rate": 0.52,
    "profit_factor": 1.30,
    "max_drawdown_pct": 4.8,
    "consultations_count": 6
  },
  "treatment_summary": {
    "bot_id": "bot_treat_01",
    "total_trades": 48,
    "win_rate": 0.61,
    "profit_factor": 1.75,
    "max_drawdown_pct": 2.4,
    "consultations_count": 6
  },
  "comparison_analysis": {
    "profit_factor_delta": 0.45,
    "win_rate_delta_pct": 9.0,
    "drawdown_delta_pct": -2.4,
    "sample_significance": true
  },
  "conclusion": "Treatment arm outperformed Control (PF: 1.75 vs 1.30, WinRate: 61.0% vs 52.0%, MaxDD: 2.40% vs 4.80%). Recommend promoting Treatment calibrations to production."
}
```

---

## Consultation Endpoint with Experiment Context

`POST /v1/trading/consult`

Submits telemetry for consultation. Can include `experiment_id`, `experiment_group` (`"CONTROL"` or `"TREATMENT"`), and `control_metrics`.

#### Request Payload (`TradingConsultRequest`)
```json
{
  "bot_id": "bot_treat_01",
  "trading_mode": "PAPER",
  "experiment_id": "exp_volatility_v2",
  "experiment_group": "TREATMENT",
  "control_metrics": {
    "profit_factor": 1.45,
    "win_rate": 0.58,
    "max_drawdown_pct": 3.2,
    "total_trades": 45
  },
  "telemetry": {
    "equity": 9200.0,
    "unrealized_pnl": -80.0,
    "realized_pnl": -800.0,
    "win_rate": 0.36,
    "profit_factor": 0.72,
    "max_drawdown_pct": 8.5,
    "consecutive_losses": 5,
    "total_trades": 42,
    "sharpe_ratio": 0.45
  },
  "strategy_performance": [
    {
      "strategy_name": "Supertrend_5m",
      "trade_count": 42,
      "win_rate": 0.36,
      "profit_factor": 0.72,
      "net_pnl": -800.0,
      "avg_win": 25.0,
      "avg_loss": 35.0,
      "consecutive_losses": 5
    }
  ],
  "current_parameters": {
    "Supertrend_5m": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.03
    }
  },
  "consultation_reason": "DRAWDOWN_EVENT"
}
```

#### Response Payload (`AIUniverseDecision`)
```json
{
  "decision_id": "e9b23fa0-82a1-4ce8-b570-0ea5cbb81b23",
  "timestamp": "2026-08-27T16:30:00.000000",
  "status": "RECOMMENDATION",
  "confidence": 0.88,
  "parameter_changes": [
    {
      "strategy": "Supertrend_5m",
      "parameter": "stop_loss_pct",
      "current_value": 0.02,
      "recommended_value": 0.0176,
      "change_pct": -12.0,
      "rationale": "Consecutive losses (5) or Max Drawdown (8.50%) on Supertrend_5m justifies tightening stop_loss_pct by 12.0% for capital preservation."
    }
  ],
  "risk_assessment": "ELEVATED RISK: Account max drawdown reached 8.50% with 5 consecutive losses. Capital preservation protocol activated.",
  "regime_analysis": "Market regime indicates chop or unfavorable volatility for current breakout/trend parameters.",
  "dissent_notes": "Critic noted that wider stop losses in this regime increase tail-risk exposure; tightening stop loss is strictly indicated.",
  "debate_summary": "Multi-Agent Deliberation:\n- TradingAnalyst: Quantitative Analysis: Evaluated win rate...\n- Strategist: Strategic Assessment: Prioritizing capital preservation...\n- Critic: Adversarial Review: Scrutinized sample size reliability...",
  "valid_until": "2026-08-28T16:30:00.000000",
  "treatment_status": "UNDERPERFORMING_CONTROL",
  "comparison_rationale": "TREATMENT arm is underperforming CONTROL baseline (Profit Factor: 0.72 vs 1.45, Drawdown: 8.50% vs 3.20%). Recommended adjustments conservatively tighten risk bounds to prevent excessive arm divergence while preserving valid test comparison.",
  "expected_improvement": "Targeting +0.73 PF recovery to regain parity with Control baseline."
}
```

---

## Best Practices for A/B Testing with AI Advisory

1. **Keep Initial Parameters Identical**: Ensure both CONTROL and TREATMENT arms start with the same underlying strategy logic and base parameters.
2. **Synchronized Telemetry Schedules**: Have both arms consult AI Universe on the same intervals (e.g. every 4 hours or after each batch of 10 closed trades).
3. **Bounded Adjustments in Treatment Arm**: AI Universe applies conservative parameter shifts ($\le 15\%$) to Treatment bots to isolate the causal impact of parameter tuning against baseline drift.
4. **Minimum Sample Size**: Allow both arms to reach at least $N \ge 20$ trades before drawing statistical conclusions or declaring an arm winner.
5. **Simultaneous Concurrency**: Both arms can consult AI Universe simultaneously without rate limit cross-contamination because rate limits are strictly isolated by unique `bot_id`.

---

## Quality Audit & Latency Benchmarks

```
================================================================================
      AI UNIVERSE — TRADING ADVISORY RECOMMENDATION QUALITY AUDIT
================================================================================

[PASS] Scenario 'telemetry_healthy.json' - Quality Score: 100/100
[PASS] Scenario 'telemetry_struggling.json' - Quality Score: 100/100
[PASS] Scenario 'telemetry_insufficient_data.json' - Quality Score: 100/100
[PASS] Scenario 'telemetry_mixed_strategies.json' - Quality Score: 100/100

================================================================================
OVERALL ADVISORY QUALITY SCORE: 100/100 (4/4 scenarios perfect)
================================================================================
```

Dual-Arm Concurrency Benchmark (`tests/test_consult_ab_load.py`):
- **Concurrent Requests**: 30 (15 simultaneous Control/Treatment pairs)
- **Success Rate**: 100.0%
- **Zero Rate Limit Interference**: Clean independent tracking per `bot_id`.
