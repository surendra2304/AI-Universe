"""Unit tests for in-process CLI commands (ask, debate, experiment)."""

import pytest
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner

from app.cli import cli_app
from app.core.orchestrator import OrchestrationResult
from app.memory.base import ExperimentRecord
from app.providers.base import ProviderResponse

runner = CliRunner()


def test_cli_ask_in_process():
    """Verify that cli 'ask' command executes in-process and outputs result."""
    mock_llm_response = ProviderResponse(
        content="In-process answer: Microservices are suitable for decoupled teams.",
        model="gemini-3.7-flash",
        provider="gemini",
        prompt_tokens=30,
        completion_tokens=20,
        total_tokens=50
    )

    with patch("app.agents.debate.model_gateway.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_llm_response

        result = runner.invoke(cli_app, ["ask", "What are the pros of microservices?", "--mode", "fast"])
        assert result.exit_code == 0
        assert "In-process answer" in result.output
        assert "Microservices are suitable" in result.output


def test_cli_debate_in_process():
    """Verify that cli 'debate' command executes in-process without requiring a running server."""
    mock_llm_response = ProviderResponse(
        content="Debate consensus: Deploy hybrid event-driven architecture.",
        model="gemini-3.7-flash",
        provider="gemini",
        prompt_tokens=40,
        completion_tokens=20,
        total_tokens=60
    )

    with patch("app.agents.debate.model_gateway.execute", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_llm_response

        result = runner.invoke(cli_app, ["debate", "Monolith vs Microservices for high scale?", "--agents", "3"])
        assert result.exit_code == 0
        assert "Debate consensus" in result.output
        assert "hybrid event-driven architecture" in result.output
