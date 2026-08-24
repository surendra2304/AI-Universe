"""Interactive Command-Line Interface (CLI) for AI Universe."""

import asyncio
import json
import sys
import httpx

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

cli_app = typer.Typer(help="AI Universe — Multi-Agent Intelligence CLI")
console = Console() if Console else None


def get_base_url() -> str:
    return f"http://{settings.HOST}:{settings.PORT}"


@cli_app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask AI Universe"),
    mode: str = typer.Option("auto", "--mode", "-m", help="Mode: auto, fast, review, debate"),
    max_agents: int = typer.Option(5, "--agents", "-a", help="Max agents to allocate"),
    budget: float = typer.Option(None, "--budget", "-b", help="Max budget in USD"),
    latency: float = typer.Option(None, "--latency", "-l", help="Max latency in seconds")
):
    """Submit a question to the orchestrator."""
    url = f"{get_base_url()}/ask"
    payload = {
        "question": question,
        "mode": mode,
        "max_agents": max_agents,
        "max_budget": budget,
        "max_latency": latency
    }

    if console:
        console.print(f"[bold cyan]Submitting query:[/bold cyan] {question}")
    else:
        print(f"Submitting query: {question}")

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if console:
                    console.print(Panel(
                        f"[bold green]Answer ({data['mode_used'].upper()} mode):[/bold green]\n\n{data['answer']}",
                        title=f"Task: {data['task_id']} (Confidence: {data['confidence']:.2f})"
                    ))
                    console.print(f"[dim]Agents: {', '.join(data['agents_used'])} | Models: {', '.join(data['models_used'])} | Latency: {data['latency_seconds']}s | Tokens: {data['total_tokens']}[/dim]")
                else:
                    print(f"\n--- Answer ({data['mode_used'].upper()} mode) ---")
                    print(data["answer"])
                    print(f"Agents: {data['agents_used']}, Latency: {data['latency_seconds']}s")
            else:
                print(f"Error ({resp.status_code}): {resp.text}")
    except Exception as exc:
        print(f"Failed to connect to AI Universe server: {exc}")


@cli_app.command()
def debate(
    question: str = typer.Argument(..., help="Complex question to debate"),
    max_agents: int = typer.Option(5, "--agents", "-a", help="Max specialists in panel")
):
    """Trigger the 6-Round Structured Multi-Agent Debate Engine."""
    url = f"{get_base_url()}/debate"
    payload = {"question": question, "max_agents": max_agents}

    if console:
        console.print(f"[bold magenta]Initiating 6-Round Debate Protocol:[/bold magenta] {question}")
    else:
        print(f"Initiating 6-Round Debate Protocol: {question}")

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if console:
                    console.print(Panel(
                        f"[bold green]Debate Consensus & Synthesis:[/bold green]\n\n{data['answer']}",
                        title=f"Debate: {data['run_id']} (Confidence: {data['confidence']:.2f})"
                    ))
                    if data.get("unresolved_disagreements"):
                        console.print("[bold yellow]Unresolved Disagreements / Preserved Dissent:[/bold yellow]")
                        for d in data["unresolved_disagreements"]:
                            console.print(f" - {d}")
                else:
                    print("\n--- Debate Consensus ---")
                    print(data["answer"])
            else:
                print(f"Error ({resp.status_code}): {resp.text}")
    except Exception as exc:
        print(f"Failed to connect to AI Universe server: {exc}")


@cli_app.command()
def experiment(
    exp_type: str = typer.Option("benchmark_suite", "--type", "-t", help="benchmark_suite, baseline_vs_debate, model_comparison"),
    question: str = typer.Option(None, "--question", "-q", help="Optional test question")
):
    """Trigger an automated benchmark or comparison experiment."""
    url = f"{get_base_url()}/experiments"
    payload = {"experiment_type": exp_type, "question": question}

    try:
        with httpx.Client(timeout=180.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                print(json.dumps(data, indent=2))
            else:
                print(f"Error ({resp.status_code}): {resp.text}")
    except Exception as exc:
        print(f"Failed to connect: {exc}")


def main():
    cli_app()


if __name__ == "__main__":
    main()
