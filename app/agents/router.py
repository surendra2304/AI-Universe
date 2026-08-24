"""Task router module for classifying problem complexity and selecting workflow mode."""

import re
from typing import List, Tuple
from app.utils.logger import logger

DEBATE_TRIGGERS: List[str] = [
    "compare", "tradeoff", "trade-off", "vs", "versus", "architecture",
    "design", "debate", "should i", "which is better", "evaluate", "critique"
]


class TaskRouter:
    """Classifies task domain and complexity to route into Fast, Review, or Debate modes."""

    def __init__(self) -> None:
        pass

    def classify_mode(self, question: str, requested_mode: str = "auto") -> Tuple[str, str]:
        """
        Determines the execution mode (fast, review, debate).
        Returns a tuple of (selected_mode, reason).
        """
        normalized_mode = requested_mode.lower().strip()
        if normalized_mode in ("fast", "review", "debate"):
            return normalized_mode, f"Explicitly requested by client: {normalized_mode}"

        # Heuristic classification for 'auto' mode
        q_lower = question.lower()
        
        # Check if question contains complex/debate triggers
        matched_triggers = [t for t in DEBATE_TRIGGERS if re.search(rf"\b{re.escape(t)}\b", q_lower)]
        if matched_triggers:
            logger.info("Task classified as 'debate' due to keywords: %s", matched_triggers)
            return "debate", f"Matched complex reasoning triggers: {', '.join(matched_triggers)}"

        # If question is short / simple query -> Fast mode
        if len(question.split()) < 30:
            logger.info("Task classified as 'fast' mode (concise direct question)")
            return "fast", "Concise factual or exploratory inquiry"

        return "review", "Moderate complexity requiring validation"


router = TaskRouter()
