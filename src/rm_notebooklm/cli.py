"""Typer-based CLI entry point.

Commands:
    sync      Download new/changed documents from reMarkable Cloud
    process   Parse + OCR downloaded documents
    upload    Upload AI response PDFs back to reMarkable
    run       Full pipeline (sync → process → upload)
    status    Show sync state and pending pages
"""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="rm-notebooklm",
    help="Sync reMarkable notes to NotebookLM/Gemini and return AI responses as PDFs.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def sync(
    dry_run: bool = typer.Option(False, "--dry-run", help="List documents without downloading"),
) -> None:
    """Download new or changed documents from reMarkable Cloud."""
    from rm_notebooklm.config import settings
    from rm_notebooklm.remarkable.auth import AuthenticationError, refresh_user_token
    from rm_notebooklm.remarkable.client import RemarkableClient
    from rm_notebooklm.remarkable.sync import SyncManager
    from rm_notebooklm.utils.logging import configure_logging

    configure_logging(level=settings.log_level, fmt=settings.log_format)

    if not settings.rm_device_token:
        console.print(
            "[red]Error:[/red] RM_DEVICE_TOKEN is not set. "
            "Run [bold]python scripts/register_device.py[/bold] first."
        )
        raise typer.Exit(code=1)

    try:
        user_token = settings.rm_user_token or refresh_user_token(settings.rm_device_token)
    except AuthenticationError as exc:
        console.print(f"[red]Authentication failed:[/red] {exc}")
        raise typer.Exit(code=1) from exc

    client = RemarkableClient(device_token=settings.rm_device_token, user_token=user_token)
    download_dir = settings.state_db_path_expanded.parent / "downloads"

    manager = SyncManager(client=client, download_dir=download_dir)
    paths = manager.sync(dry_run=dry_run)

    if not dry_run:
        console.print(f"[green]Synced {len(paths)} new document(s)[/green]")


@app.command()
def process(
    dry_run: bool = typer.Option(False, "--dry-run", help="Parse without calling OCR APIs"),
) -> None:
    """Parse downloaded .rm files and run OCR on handwriting pages."""
    raise NotImplementedError("Milestone 2/3: implement process command")


@app.command()
def upload(
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate PDFs without uploading"),
) -> None:
    """Upload AI response PDFs back to reMarkable Cloud."""
    raise NotImplementedError("Milestone 5: implement upload command")


@app.command()
def run(
    dry_run: bool = typer.Option(False, "--dry-run", help="Run pipeline without any writes"),
    notebook_filter: str | None = typer.Option(
        None, "--notebook-filter", help="Filter by notebook name"
    ),
) -> None:
    """Run the full pipeline: sync → process → query → upload."""
    raise NotImplementedError("Milestone 6: implement run command")


@app.command()
def status() -> None:
    """Show last sync time, pending pages, and SQLite state summary."""
    raise NotImplementedError("Milestone 6: implement status command")


if __name__ == "__main__":
    app()
