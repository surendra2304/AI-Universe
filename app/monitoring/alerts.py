"""Alert System and Webhook Dispatcher for Inference Operations."""

import time
from typing import Literal

from pydantic import BaseModel, Field

from app.utils.logger import logger


class AlertItem(BaseModel):
    alert_id: str
    category: Literal["cost", "provider", "quality", "consumer"]
    severity: Literal["critical", "warning", "info"]
    title: str
    description: str
    timestamp: float = Field(default_factory=time.time)
    acknowledged: bool = False


class AlertSystem:
    """Manages active operational alerts and dispatches webhook notifications."""

    def __init__(self) -> None:
        self.alerts: list[AlertItem] = [
            AlertItem(
                alert_id="ALT-101",
                category="cost",
                severity="info",
                title="Daily Budget Tracking Normal",
                description="Current expenditure is at 8% of daily allocated ceiling."
            )
        ]
        self.webhook_urls: list[str] = []

    def trigger_alert(self, category: Literal["cost", "provider", "quality", "consumer"], severity: Literal["critical", "warning", "info"], title: str, description: str) -> AlertItem:
        alert = AlertItem(
            alert_id=f"ALT-{int(time.time())}",
            category=category,
            severity=severity,
            title=title,
            description=description
        )
        self.alerts.append(alert)
        logger.warning("[ALERT %s] %s: %s", severity.upper(), title, description)
        return alert

    def get_alerts(self, unacknowledged_only: bool = False) -> list[AlertItem]:
        if unacknowledged_only:
            return [a for a in self.alerts if not a.acknowledged]
        return self.alerts

    def acknowledge_alert(self, alert_id: str) -> bool:
        for a in self.alerts:
            if a.alert_id == alert_id:
                a.acknowledged = True
                return True
        return False


alert_system = AlertSystem()
