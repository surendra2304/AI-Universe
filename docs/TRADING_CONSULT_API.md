# Trading Consultation API Reference

The **Trading Consultation API** exposes AI Universe as an asynchronous advisory intelligence layer for autonomous trading bots. It provides multi-agent deliberation over quantitative performance metrics, parameter adjustments, and drawdown risk assessments.

> [!IMPORTANT]
> **Safety Rule & Invariant**: AI Universe is strictly an **advisory system**. It never interacts with exchange endpoints, never holds or signs private keys, and never executes trades. Trading bots independently validate all returned parameter recommendations against hard deterministic safety bounds.

---

## Architecture Overview

When a trading bot submits performance telemetry, AI Universe convenes a dedicated multi-agent specialist panel:
1. **Trading Analyst (`trading_analyst`)**: Analyzes win rate, profit factor, drawdown curves, and consecutive loss streaks to propose initial parameter calibrations.
2. **Strategist (`strategist`)**: Evaluates trade-offs between capital preservation and trade frequency across active strategies.
3. **Adversarial Critic (`critic`)**: Challenges curve-fitting risks, small-sample overfitting, and regime shifts.
4. **Data Analyst (`data_analyst`)**: Quantitatively verifies empirical distributions and mathematical significance thresholds.
5. **Synthesizer (`synthesizer`)**: Emits a bounded `AIUniverseDecision` respecting hard constraints.

### Synthesis Decision Rules
- **Maximum 2 parameter adjustments** per decision (prefers 1).
- **Mandatory Quantitative Evidence**: Every adjustment must cite specific telemetry metrics (e.g. *"consecutive_losses=6 justifies tightening stop_loss_pct by 15%"*).
- **Sample Size Gate**: If total closed trades $N < 20$, the system strictly returns `status = "INSUFFICIENT_DATA"`.
- **Healthy Gate**: If win rate $\ge 50\%$, profit factor $\ge 1.25$, and max drawdown $\le 5\%$, the system returns `status = "NO_CHANGE"`.

---

## Endpoints

### 1. Request Consultation
`POST /v1/trading/consult`

Submits trading bot telemetry for multi-agent advisory review.

#### Headers
- `Content-Type: application/json`

#### Request Payload (`TradingConsultRequest`)
```json
{
  "bot_id": "crypto_scalper_01",
  "trading_mode": "PAPER",
  "experiment_id": "exp_v2_volatility_test",
  "telemetry": {
    "equity": 9450.0,
    "unrealized_pnl": -50.0,
    "realized_pnl": -550.0,
    "win_rate": 0.41,
    "profit_factor": 0.82,
    "max_drawdown_pct": 7.4,
    "consecutive_losses": 5,
    "total_trades": 48,
    "sharpe_ratio": 0.65
  },
  "strategy_performance": [
    {
      "strategy_name": "Supertrend_5m",
      "trade_count": 32,
      "win_rate": 0.38,
      "profit_factor": 0.75,
      "net_pnl": -420.0,
      "avg_win": 28.0,
      "avg_loss": 32.0,
      "consecutive_losses": 4
    }
  ],
  "current_parameters": {
    "Supertrend_5m": {
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.03,
      "atr_multiplier": 2.5
    }
  },
  "regime_data": {
    "volatility_regime": "high_chop",
    "trend_strength": "weak"
  },
  "recent_trades": [
    {
      "id": "trade_101",
      "side": "BUY",
      "entry_price": 64200.0,
      "exit_price": 63800.0,
      "pnl": -40.0,
      "duration_sec": 420
    }
  ],
  "consultation_reason": "DRAWDOWN_EVENT"
}
```

#### Response Payload (`AIUniverseDecision`)
```json
{
  "decision_id": "e9b23fa0-82a1-4ce8-b570-0ea5cbb81b23",
  "timestamp": "2026-08-27T13:30:00.000000",
  "status": "RECOMMENDATION",
  "confidence": 0.88,
  "parameter_changes": [
    {
      "strategy": "Supertrend_5m",
      "parameter": "stop_loss_pct",
      "current_value": 0.02,
      "recommended_value": 0.017,
      "change_pct": -15.0,
      "rationale": "Consecutive losses (5) or Max Drawdown (7.40%) on Supertrend_5m justifies tightening stop_loss_pct by 15.0% for capital preservation."
    }
  ],
  "risk_assessment": "ELEVATED RISK: Account max drawdown reached 7.40% with 5 consecutive losses. Capital preservation protocol activated.",
  "regime_analysis": "Market regime indicates chop or unfavorable volatility for current breakout/trend parameters.",
  "dissent_notes": "Critic noted that wider stop losses in this regime increase tail-risk exposure; tightening stop loss is strictly indicated.",
  "debate_summary": "Multi-Agent Deliberation:\n- TradingAnalyst: Quantitative Analysis: Evaluated win rate...\n- Strategist: Strategic Assessment: Prioritizing capital preservation...\n- Critic: Adversarial Review: Scrutinized sample size reliability...",
  "valid_until": "2026-08-28T13:30:00.000000"
}
```

---

### 2. Consultation Subsystem Health
`GET /v1/trading/consult/health`

#### Response
```json
{
  "status": "ok",
  "service": "trading_consultation",
  "agents_available": [
    "Researcher",
    "Architect",
    "Coder",
    "Debugger",
    "Security Analyst",
    "Data Analyst",
    "Critic",
    "Fact Checker",
    "Strategist",
    "Synthesizer",
    "Trading Analyst"
  ],
  "advisory_only": true,
  "exchange_execution": false
}
```

---

### 3. Retrieve Historical Decision
`GET /v1/trading/decisions/{decision_id}`

Retrieves an advisory decision previously generated and persisted in SQLite memory.

---

## Rate Limiting & Abuse Prevention

1. **Rate Limiting**: Sliding window maximum of **20 consultations per `bot_id` per hour** (`HTTP 429 Too Many Requests` on breach).
2. **Payload Size Guard**: Maximum payload size of **1MB** (`HTTP 413 Payload Too Large`).
3. **Zero Credential Guard**: Any incoming payload containing sensitive credential keys (`api_key`, `secret`, `private_key`, `credential`, etc.) is rejected immediately with `HTTP 400 Bad Request`.
4. **Server Timeout**: 180-second timeout on multi-agent debate orchestration; gracefully returns a safe holding pattern (`status = "NO_CHANGE"`) if timeout is reached.
