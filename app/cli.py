"""Interactive Command-Line Interface (CLI) for AI Universe.

Executes directly in-process using the Orchestrator and SQLiteMemory without
requiring a running uvicorn background server.
"""

import asyncio
import json
import sys
from typing import Optional

try:
    import typer
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
except ImportError:
    import click as typer
    Console = None
    Panel = None
    Table = None

from app.core.config import settings
from app.core.orchestrator import OrchestrationRequest, Orchestrator
from app.memory.sqlite import SQLiteMemory
from app.experiments.harness import BenchmarkHarness, ExperimentRunRequest

# Configure UTF-8 safe console for Windows terminal
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

cli_app = typer.Typer(help="AI Universe — Multi-Agent Intelligence CLI")
console = Console(legacy_windows=False) if Console else None


async def _run_in_process_ask(
    question: str,
    mode: str = "auto",
    max_agents: int = 5,
    budget: Optional[float] = None,
    latency: Optional[float] = None
) -> None:
    """Instantiate orchestrator and run task directly in-process."""
    memory = SQLiteMemory()
    await memory.initialize()
    orch = Orchestrator(memory=memory)

    req = OrchestrationRequest(
        question=question,
        mode=mode,
        max_agents=max_agents,
        max_budget=budget,
        max_latency=latency
    )

    if console:
        console.print(f"[bold cyan]Processing query in-process:[/bold cyan] {question}")
    else:
        print(f"Processing query in-process: {question}")

    try:
        res = await orch.process_task(req)
        if console:
            console.print(Panel(
                f"[bold green]Answer ({res.mode_used.upper()} mode | Complexity: {res.complexity.upper()}):[/bold green]\n\n{res.answer}",
                title=f"Task: {res.task_id} (Confidence: {res.confidence:.2f})"
            ))
            console.print(
                f"[dim]Agents: {', '.join(res.agents_used)} | "
                f"Models: {', '.join(res.models_used)} | "
                f"Latency: {res.total_latency_seconds:.2f}s | "
                f"Tokens: {res.total_tokens}[/dim]"
            )
            if res.unresolved_disagreements:
                console.print("[bold yellow]Unresolved Disagreements / Preserved Dissent:[/bold yellow]")
                for d in res.unresolved_disagreements:
                    console.print(f" - {d}")
        else:
            print(f"\n--- Answer ({res.mode_used.upper()} mode | Complexity: {res.complexity.upper()}) ---")
            print(res.answer)
            print(f"Agents: {res.agents_used} | Latency: {res.total_latency_seconds:.2f}s | Tokens: {res.total_tokens}")
    except Exception as exc:
        if console:
            console.print(f"[bold red]Execution error:[/bold red] {exc}")
        else:
            print(f"Execution error: {exc}")


async def _run_in_process_debate(
    question: str,
    max_agents: int = 5
) -> None:
    """Instantiate orchestrator and run multi-agent debate directly in-process."""
    memory = SQLiteMemory()
    await memory.initialize()
    orch = Orchestrator(memory=memory)

    req = OrchestrationRequest(
        question=question,
        mode="debate",
        max_agents=max_agents
    )

    if console:
        console.print(f"[bold magenta]Initiating Dynamic Multi-Agent Debate Protocol:[/bold magenta] {question}")
    else:
        print(f"Initiating Dynamic Multi-Agent Debate Protocol: {question}")

    try:
        res = await orch.process_task(req)
        if console:
            console.print(Panel(
                f"[bold green]Debate Consensus & Synthesis:[/bold green]\n\n{res.answer}",
                title=f"Debate: {res.run_id} (Confidence: {res.confidence:.2f} | Complexity: {res.complexity.upper()})"
            ))
            console.print(
                f"[dim]Agents: {', '.join(res.agents_used)} | "
                f"Models: {', '.join(res.models_used)} | "
                f"Latency: {res.total_latency_seconds:.2f}s | "
                f"Tokens: {res.total_tokens}[/dim]"
            )
            if res.unresolved_disagreements:
                console.print("[bold yellow]Unresolved Disagreements / Preserved Dissent:[/bold yellow]")
                for d in res.unresolved_disagreements:
                    console.print(f" - {d}")
        else:
            print(f"\n--- Debate Consensus (Complexity: {res.complexity.upper()}) ---")
            print(res.answer)
            print(f"Agents: {res.agents_used} | Latency: {res.total_latency_seconds:.2f}s | Tokens: {res.total_tokens}")
    except Exception as exc:
        if console:
            console.print(f"[bold red]Execution error:[/bold red] {exc}")
        else:
            print(f"Execution error: {exc}")


async def _run_in_process_experiment(
    exp_type: str = "benchmark_suite",
    question: Optional[str] = None
) -> None:
    """Run an automated experiment in-process."""
    memory = SQLiteMemory()
    await memory.initialize()
    orch = Orchestrator(memory=memory)
    harness = BenchmarkHarness(memory=memory, orchestrator=orch)

    try:
        if exp_type == "benchmark_suite":
            rec = await harness.run_benchmark_suite()
        elif exp_type == "baseline_vs_debate":
            q = question or "Should AI Universe use microservices or monolithic architecture?"
            rec = await harness.run_baseline_vs_debate_comparison(q)
        else:
            rec = await harness.run_benchmark_suite()

        if console:
            console.print(Panel(
                json.dumps(rec.model_dump(), indent=2, default=str),
                title=f"Experiment: {rec.id} ({rec.status})"
            ))
        else:
            print(json.dumps(rec.model_dump(), indent=2, default=str))
    except Exception as exc:
        if console:
            console.print(f"[bold red]Experiment error:[/bold red] {exc}")
        else:
            print(f"Experiment error: {exc}")


@cli_app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask AI Universe"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Mode: auto, fast, review, debate"),
    max_agents: int = typer.Option(5, "--agents", "-a", help="Max agents to allocate"),
    budget: Optional[float] = typer.Option(None, "--budget", "-b", help="Max budget in USD"),
    latency: Optional[float] = typer.Option(None, "--latency", "-l", help="Max latency in seconds")
):
    """Submit a question to the orchestrator directly in-process."""
    asyncio.run(_run_in_process_ask(question, mode=mode, max_agents=max_agents, budget=budget, latency=latency))


@cli_app.command()
def debate(
    question: str = typer.Argument(..., help="Complex question to debate"),
    max_agents: int = typer.Option(5, "--agents", "-a", help="Max specialists in panel")
):
    """Trigger the Multi-Agent Collaboration & Debate Engine directly in-process."""
    asyncio.run(_run_in_process_debate(question, max_agents=max_agents))


@cli_app.command()
def experiment(
    exp_type: str = typer.Option("benchmark_suite", "--type", "-t", help="benchmark_suite, baseline_vs_debate, model_comparison"),
    question: Optional[str] = typer.Option(None, "--question", "-q", help="Optional test question")
):
    """Trigger an automated benchmark or comparison experiment directly in-process."""
    asyncio.run(_run_in_process_experiment(exp_type=exp_type, question=question))


def main():
    cli_app()


if __name__ == "__main__":
    main()
