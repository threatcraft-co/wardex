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
def start():
    """Start the wardex daemon in the foreground."""
    from wardex.daemon import run

    console.print("[bold green]Starting wardex daemon...[/bold green]")
    run()


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