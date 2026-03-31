"""Click-based CLI for dbtcloud-importer."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from .bootstrap import run, run_add


@click.group()
def cli() -> None:
    """Import existing dbt Cloud account state into Terraform YAML configuration.

    Credentials are read from environment variables (or a .env file):

    \b
        DBT_SOURCE_HOST_URL   — e.g. https://cloud.getdbt.com
        DBT_SOURCE_ACCOUNT_ID — numeric account ID
        DBT_SOURCE_API_TOKEN  — service token or personal access token
    """


@cli.command("init")
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    metavar="PATH",
    help="Output path for dbt-config.yml (default: ./dbt-config.yml)",
)
@click.option(
    "--project-id",
    "project_ids",
    type=int,
    multiple=True,
    metavar="ID",
    help="Scope import to a project ID (repeatable: --project-id 123 --project-id 456)",
)
@click.option(
    "--slim",
    is_flag=True,
    default=False,
    help="Skip account-level globals (groups, service tokens, notifications, etc.). "
    "Connections and repositories are always fetched.",
)
@click.option(
    "--import-blocks",
    is_flag=True,
    default=False,
    help="Generate imports.tf with Terraform import {} blocks for all fetched resources "
    "(requires Terraform >= 1.5). Safe to delete after first 'terraform apply'.",
)
def init_command(
    output: Optional[Path],
    project_ids: tuple[int, ...],
    slim: bool,
    import_blocks: bool,
) -> None:
    """Bootstrap a new dbt Cloud Terraform project.

    Fetches account state and writes dbt-config.yml (and optionally imports.tf)
    to the current directory.
    """
    run(
        output_path=output,
        project_ids=list(project_ids) if project_ids else None,
        slim=slim,
        import_blocks=import_blocks,
    )


@cli.command("add")
@click.option(
    "--project-id",
    "project_ids",
    type=int,
    multiple=True,
    required=True,
    metavar="ID",
    help="Project ID to include in regenerated dbt-config.yml (repeatable; include ALL projects, existing + new)",
)
@click.option(
    "--new-project-id",
    "new_project_ids",
    type=int,
    multiple=True,
    required=True,
    metavar="ID",
    help="Project ID that is NEW and needs import blocks (repeatable)",
)
@click.option(
    "--output",
    type=click.Path(path_type=Path),
    default=None,
    metavar="PATH",
    help="Output path for dbt-config.yml (default: ./dbt-config.yml)",
)
def add_command(
    project_ids: tuple[int, ...],
    new_project_ids: tuple[int, ...],
    output: Optional[Path],
) -> None:
    """Add a new project to an existing Terraform setup.

    Re-generates dbt-config.yml for all specified projects and writes
    imports.tf scoped only to the new project(s) — no conflicts with
    resources already in Terraform state.

    \b
    Example:
      dbtcloud-import add \\
        --project-id 123 --project-id 456 \\
        --new-project-id 456
    """
    run_add(
        output_path=output,
        project_ids=list(project_ids),
        new_project_ids=list(new_project_ids),
    )
