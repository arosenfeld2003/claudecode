"""OpenClaw Moltbook Monitor - CLI Application.

Provides commands for monitoring, analysis, and status checking.
All operations run through the reverse proxy for security.
"""

import json
from datetime import UTC, datetime
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from monitor.health import HealthChecker

app = typer.Typer(
    name="monitor",
    help="OpenClaw Moltbook Monitor - Safely monitor and analyze the Moltbook platform",
    no_args_is_help=True,
)

console = Console()


def get_output_format(format_type: str) -> str:
    """Validate and return output format."""
    valid_formats = ["text", "json"]
    if format_type not in valid_formats:
        raise typer.BadParameter(f"Format must be one of: {', '.join(valid_formats)}")
    return format_type


@app.callback()
def main(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose output for debugging"),
    ] = False,
) -> None:
    """OpenClaw Moltbook Monitor CLI."""
    if verbose:
        console.print("[dim]Verbose mode enabled[/dim]")


@app.command()
def health(
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Check health status of all monitor components.

    Verifies database connectivity, proxy connectivity, and overall system health.
    """
    checker = HealthChecker()
    status = checker.check_all()

    if format_type == "json":
        console.print(json.dumps(status, indent=2, default=str))
    else:
        table = Table(title="Health Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details")

        overall_healthy = True
        for component, details in status.items():
            if component in ("timestamp", "healthy"):
                continue
            if not isinstance(details, dict):
                continue
            is_healthy = details.get("healthy", False)
            overall_healthy = overall_healthy and is_healthy
            status_str = "[green]healthy[/green]" if is_healthy else "[red]unhealthy[/red]"
            detail_str = details.get("message", "")
            table.add_row(component, status_str, detail_str)

        console.print(table)
        console.print(f"\nTimestamp: {status.get('timestamp', 'unknown')}")

        if not overall_healthy:
            raise typer.Exit(code=1)


@app.command()
def status(
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Show current monitoring status.

    Displays poll state, rate limit status, database stats, and uptime.
    """
    # Placeholder - will be implemented in Phase 5
    status_data = {
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "not_implemented",
        "message": "Status command will be fully implemented in Phase 5",
    }

    if format_type == "json":
        console.print(json.dumps(status_data, indent=2))
    else:
        console.print("[yellow]Status command not yet fully implemented[/yellow]")
        console.print("This will show poll state, rate limits, and database stats.")


@app.command()
def stream(
    submolt: Annotated[
        str | None,
        typer.Option("--submolt", "-s", help="Filter by submolt name"),
    ] = None,
    theme: Annotated[
        str | None,
        typer.Option("--theme", "-t", help="Filter by theme name"),
    ] = None,
    goal: Annotated[
        str | None,
        typer.Option("--goal", "-g", help="Filter by research goal"),
    ] = None,
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Show live tagged feed from Moltbook.

    Displays posts with timestamp, agent, submolt, title, themes, and confidence.
    """
    # Placeholder - will be implemented in Phase 5
    console.print("[yellow]Stream command not yet implemented[/yellow]")
    console.print("This will show live tagged feed with:")
    console.print("  - Timestamp, agent_id, submolt, title")
    console.print("  - Assigned themes and confidence scores")
    if submolt:
        console.print(f"  - Filtered by submolt: {submolt}")
    if theme:
        console.print(f"  - Filtered by theme: {theme}")
    if goal:
        console.print(f"  - Filtered by goal: {goal}")


@app.command()
def themes(
    goal: Annotated[
        str | None,
        typer.Option("--goal", "-g", help="Filter by research goal"),
    ] = None,
    evolve: Annotated[
        bool,
        typer.Option("--evolve", help="Show theme taxonomy evolution changelog"),
    ] = False,
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """List discovered themes with research goal mapping.

    Shows theme names, descriptions, post counts, and trending status.
    """
    # Placeholder - will be implemented in Phase 5
    console.print("[yellow]Themes command not yet implemented[/yellow]")
    if evolve:
        console.print("This will show theme taxonomy evolution changelog")
    else:
        console.print("This will list discovered themes with:")
        console.print("  - Name, description, research goals")
        console.print("  - Post count and trending status")
    if goal:
        console.print(f"  - Filtered by goal: {goal}")


@app.command()
def trends(
    window: Annotated[
        str,
        typer.Option("--window", "-w", help="Time window: 1h, 6h, 24h, or 7d"),
    ] = "1h",
    format_type: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: text or json"),
    ] = "text",
) -> None:
    """Show current trending themes and activity.

    Displays themes with post count, velocity, and spike detection.
    """
    # Placeholder - will be implemented in Phase 5
    valid_windows = ["1h", "6h", "24h", "7d"]
    if window not in valid_windows:
        console.print(f"[red]Invalid window. Must be one of: {', '.join(valid_windows)}[/red]")
        raise typer.Exit(code=1)

    console.print("[yellow]Trends command not yet implemented[/yellow]")
    console.print(f"This will show trending themes for window: {window}")


@app.command()
def version() -> None:
    """Show version information."""
    from monitor import __version__

    console.print(f"OpenClaw Moltbook Monitor v{__version__}")


if __name__ == "__main__":
    app()
