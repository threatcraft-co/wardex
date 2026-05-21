"""Wardex CLI entrypoint."""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option()
def cli():
    """Wardex — warden for your VS Code extensions."""
    pass


@cli.command()
@click.option("--enforce", is_flag=True, help="Quarantine unverified extensions (default: alert only)")
@click.option(
    "--extensions-dir",
    type=click.Path(),
    default=None,
    help="VS Code extensions directory to watch",
)
def start(enforce, extensions_dir):
    """Start the wardex daemon in the foreground."""
    from pathlib import Path
    from wardex.daemon import DEFAULT_EXTENSIONS_DIR, run

    ext_dir = Path(extensions_dir).expanduser() if extensions_dir else DEFAULT_EXTENSIONS_DIR

    mode_label = "[bold red]ENFORCE[/bold red]" if enforce else "[bold yellow]ALERT[/bold yellow]"
    console.print(f"[bold green]Starting wardex[/bold green] in {mode_label} mode")
    console.print(f"Watching: {ext_dir}")
    run(extensions_dir=ext_dir, enforce=enforce)


@cli.command()
def status():
    """Show daemon health and recent activity."""
    console.print("[yellow]Status command not yet implemented[/yellow]")


@cli.command()
def audit():
    """Scan currently installed extensions against policy."""
    console.print("[yellow]Audit command not yet implemented[/yellow]")


@cli.group()
def allowlist():
    """Manage the publisher and extension allowlist."""
    pass


@allowlist.command("add")
@click.argument("identifier")
@click.option("--publisher", is_flag=True, help="Treat identifier as a publisher, not an extension")
def allowlist_add(identifier, publisher):
    """Add an extension or publisher to the allowlist."""
    kind = "publisher" if publisher else "extension"
    console.print(f"[green]Would add {kind}:[/green] {identifier}")


if __name__ == "__main__":
    cli()