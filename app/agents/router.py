"""Task router module for classifying problem complexity and selecting specialist agents."""

import re
from typing import List, Tuple
from pydantic import BaseModel, Field
from app.utils.logger import logger

DEBATE_TRIGGERS: List[str] = [
    "compare", "tradeoff", "trade-off", "vs", "versus", "architecture",
    "design", "debate", "should i", "which is better", "evaluate", "critique",
    "pros and cons", "alternatives"
]

DOMAIN_KEYWORD_MAP = {
    "debugger": ["debug", "error", "traceback", "crash", "deadlock", "exception", "bug", "failure", "fail", "broken"],
    "security_analyst": ["security", "vulnerability", "auth", "threat", "injection", "permission", "leak", "secret", "attack"],
    "data_analyst": ["data", "sql", "metric", "statistics", "table", "dataset", "dataframe", "chart", "distribution"],
    "coder": ["code", "implement", "function", "refactor", "algorithm", "class", "syntax", "python", "fastapi", "write a"],
    "architect": ["architecture", "system design", "modular", "scalability", "pipeline", "schema design", "microservice"],
    "fact_checker": ["verify", "is it true", "fact", "check claim", "verifiable", "source", "accuracy"],
    "strategist": ["strategy", "priority", "roadmap", "decision", "trade-off", "cost-benefit", "plan"],
    "critic": ["critique", "red team", "weakness", "fallacy", "attack", "counterexample"],
}


class RoutingDecision(BaseModel):
    """Result of task complexity and agent allocation analysis."""
    mode: str = Field(description="fast, review, or debate")
    reason: str = Field(description="Explanation of routing rationale")
    selected_agent_ids: List[str] = Field(description="Ordered list of agent IDs assigned to the task")


class TaskRouter:
    """Classifies task domain and complexity to route into Fast, Review, or Debate modes with specialist panels."""

    def detect_domain_specialist(self, question: str) -> str:
        """Detect the single most relevant specialist for a given query."""
        q_lower = question.lower()
        for agent_id, keywords in DOMAIN_KEYWORD_MAP.items():
            if any(re.search(rf"\b{re.escape(kw)}\b", q_lower) for kw in keywords):
                return agent_id
        return "researcher"

    def select_review_pair(self, question: str) -> List[str]:
        """Select two complementary agents for Review mode."""
        primary = self.detect_domain_specialist(question)
        if primary == "coder":
            return ["coder", "critic"]
        elif primary == "architect":
            return ["architect", "security_analyst"]
        elif primary == "security_analyst":
            return ["security_analyst", "architect"]
        elif primary == "debugger":
            return ["debugger", "coder"]
        elif primary == "data_analyst":
            return ["data_analyst", "fact_checker"]
        else:
            return [primary, "critic"]

    def select_debate_panel(self, question: str, max_agents: int = 5) -> List[str]:
        """Assemble a diverse panel of 3-5 specialists for structured debate."""
        primary = self.detect_domain_specialist(question)
        panel: List[str] = []

        # Always include the domain primary specialist
        panel.append(primary)

        # Core debate participants
        candidates = ["architect", "security_analyst", "coder", "critic", "strategist", "fact_checker", "data_analyst"]
        for cand in candidates:
            if cand not in panel and len(panel) < max_agents:
                panel.append(cand)

        # Always ensure Critic is in the debate panel if space allows
        if "critic" not in panel and len(panel) > 1:
            panel[-1] = "critic"

        return panel[:max_agents]

    def classify_mode(self, question: str, requested_mode: str = "auto") -> Tuple[str, str]:
        """
        Determines the execution mode (fast, review, debate).
        Returns a tuple of (selected_mode, reason).
        """
        normalized_mode = requested_mode.lower().strip()
        if normalized_mode in ("fast", "review", "debate"):
            return normalized_mode, f"Explicitly requested by client: {normalized_mode}"

        q_lower = question.lower()
        matched_triggers = [t for t in DEBATE_TRIGGERS if re.search(rf"\b{re.escape(t)}\b", q_lower)]
        if matched_triggers:
            return "debate", f"Matched complex reasoning triggers: {', '.join(matched_triggers)}"

        if len(question.split()) < 30:
            return "fast", "Concise factual or exploratory inquiry"

        return "review", "Moderate complexity requiring validation"

    def route_task(
        self,
        question: str,
        requested_mode: str = "auto",
        max_agents: int = 5
    ) -> RoutingDecision:
        """Full routing decision returning mode, reason, and selected specialist agent IDs."""
        mode, reason = self.classify_mode(question, requested_mode)

        if mode == "fast":
            agent_id = self.detect_domain_specialist(question)
            selected = [agent_id]
        elif mode == "review":
            selected = self.select_review_pair(question)
        else:  # debate
            selected = self.select_debate_panel(question, max_agents=max_agents)

        logger.info(
            "Task routed to mode '%s' with agents %s (Reason: %s)",
            mode, selected, reason
        )
        return RoutingDecision(
            mode=mode,
            reason=reason,
            selected_agent_ids=selected
        )


router = TaskRouter()
