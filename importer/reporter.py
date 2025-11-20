"""Generate human-readable reports from account snapshots."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from . import get_version

if TYPE_CHECKING:
    from .models import AccountSnapshot


def generate_summary_report(snapshot: AccountSnapshot) -> str:
    """Generate a high-level summary with counts by object type."""
    lines = [
        "# dbt Cloud Account Import Summary",
        "",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Importer Version:** {get_version()}",
        f"**Account ID:** {snapshot.account_id}",
        f"**Account Name:** {snapshot.account_name or 'N/A'}",
        "",
        "## Global Resources",
        "",
        f"- **Connections:** {len(snapshot.globals.connections)}",
        f"- **Repositories:** {len(snapshot.globals.repositories)}",
        "",
        "## Projects Overview",
        "",
        f"**Total Projects:** {len(snapshot.projects)}",
        "",
    ]

    # Calculate aggregated counts across all projects
    total_envs = sum(len(p.environments) for p in snapshot.projects)
    total_jobs = sum(len(p.jobs) for p in snapshot.projects)
    total_env_vars = 0
    total_secret_vars = 0
    
    for p in snapshot.projects:
        for var in p.environment_variables:
            var_name = getattr(var, "name", "")
            if var_name.startswith("DBT_ENV_SECRET"):
                total_secret_vars += 1
            else:
                total_env_vars += 1

    lines.extend(
        [
            "### Aggregate Counts",
            "",
            f"- **Total Environments:** {total_envs}",
            f"- **Total Jobs:** {total_jobs}",
            f"- **Total Environment Variables:** {total_env_vars}",
            f"- **Total Environment Variable Secrets:** {total_secret_vars}",
            "",
            "---",
            "",
            "## Projects Detail",
            "",
        ]
    )

    # Per-project breakdown
    for project in sorted(snapshot.projects, key=lambda p: p.name):
        project_envs = len(project.environments)
        project_jobs = len(project.jobs)
        
        # Count regular and secret variables
        project_vars = 0
        project_secrets = 0
        for var in project.environment_variables:
            var_name = getattr(var, "name", "")
            if var_name.startswith("DBT_ENV_SECRET"):
                project_secrets += 1
            else:
                project_vars += 1

        lines.extend(
            [
                f"### {project.name} (PRJ ID: {project.id})",
                "",
                f"- **Environments:** {project_envs}",
                f"- **Jobs:** {project_jobs}",
                f"- **Environment Variables:** {project_vars}",
                f"- **Environment Variable Secrets:** {project_secrets}",
                "",
            ]
        )

    return "\n".join(lines)


def generate_detailed_outline(snapshot: AccountSnapshot) -> str:
    """Generate a detailed tree outline showing IDs and names."""
    lines = [
        "# dbt Cloud Account Detailed Outline",
        "",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Importer Version:** {get_version()}",
        "",
        "## Account",
        "",
        f"- **ID:** {snapshot.account_id}",
        f"- **Name:** {snapshot.account_name or 'N/A'}",
        "",
        "---",
        "",
        "## Global Resources",
        "",
    ]

    # Connections
    if snapshot.globals.connections:
        lines.append("### Connections")
        lines.append("")
        lines.append("| Key | ID | Name | Type |")
        lines.append("|-----|----|----- |------|")
        for key, conn in sorted(snapshot.globals.connections.items()):
            conn_id = conn.id or "N/A"
            conn_name = conn.name or "N/A"
            conn_type = conn.type or "N/A"
            lines.append(f"| `{key}` | {conn_id} | {conn_name} | {conn_type} |")
        lines.append("")

    # Repositories
    if snapshot.globals.repositories:
        lines.append("### Repositories")
        lines.append("")
        lines.append("| Key | ID | Remote URL | Clone Strategy |")
        lines.append("|-----|----|-----------:|----------------|")
        for key, repo in sorted(snapshot.globals.repositories.items()):
            repo_id = repo.id or "N/A"
            remote = repo.remote_url or "N/A"
            clone_strategy = repo.git_clone_strategy or "N/A"
            lines.append(f"| `{key}` | {repo_id} | {remote} | {clone_strategy} |")
        lines.append("")

    lines.extend(["---", "", "## Projects", ""])

    # Projects tree
    for idx, project in enumerate(sorted(snapshot.projects, key=lambda p: p.name)):
        if idx > 0:
            lines.append("---")
            lines.append("---")
            lines.append("---")
            lines.append("")
        
        lines.append(f"### {project.name}")
        lines.append("")
        lines.append(f"  - **Project ID:** {project.id}")
        lines.append(f"  - **Key:** `{project.key}`")
        if project.repository_key:
            lines.append(f"  - **Repository:** `{project.repository_key}`")
        lines.append("")

        # Environment variables (split into regular and secrets)
        if project.environment_variables:
            regular_vars = []
            secret_vars = []
            
            for var in project.environment_variables:
                var_name = getattr(var, "name", "Unnamed")
                if var_name.startswith("DBT_ENV_SECRET"):
                    secret_vars.append(var)
                else:
                    regular_vars.append(var)
            
            # Regular environment variables
            if regular_vars:
                lines.append("#### Environment Variables")
                lines.append("")
                for var in regular_vars:
                    var_name = getattr(var, "name", "Unnamed")
                    project_default = getattr(var, "project_default", None)
                    env_values = getattr(var, "environment_values", {})
                    
                    # Build the header line
                    total_values = len(env_values) + (1 if project_default else 0)
                    lines.append(f"**`{var_name}`** — {total_values} value(s)")
                    lines.append("")
                    
                    # Create a table for values
                    if project_default or env_values:
                        lines.append("| Environment | Value |")
                        lines.append("|-------------|-------|")
                        
                        # Show project default if it exists
                        if project_default:
                            lines.append(f"| Project (default) | `{project_default}` |")
                        
                        # Show environment-specific values
                        if env_values:
                            for env_name, value in sorted(env_values.items()):
                                lines.append(f"| {env_name} | `{value}` |")
                        
                        lines.append("")
                lines.append("")
            
            # Secret environment variables
            if secret_vars:
                lines.append("#### Environment Variable Secrets")
                lines.append("")
                for var in secret_vars:
                    var_name = getattr(var, "name", "Unnamed")
                    project_default = getattr(var, "project_default", None)
                    env_values = getattr(var, "environment_values", {})
                    
                    # Build the header line
                    total_values = len(env_values) + (1 if project_default else 0)
                    lines.append(f"**`{var_name}`** — {total_values} value(s)")
                    lines.append("")
                    
                    # Create a table showing masked values
                    if project_default or env_values:
                        lines.append("| Environment | Value |")
                        lines.append("|-------------|-------|")
                        
                        # Show project default (masked)
                        if project_default:
                            lines.append(f"| Project (default) | `{project_default}` |")
                        
                        # Show environment-specific values (masked)
                        if env_values:
                            for env_name, value in sorted(env_values.items()):
                                lines.append(f"| {env_name} | `{value}` |")
                        
                        lines.append("")
                lines.append("")

        # Environments
        if project.environments:
            lines.append("#### Environments")
            lines.append("")
            for env in project.environments:
                env_name = getattr(env, "name", "Unnamed")
                env_id = getattr(env, "id", "N/A")
                env_type = getattr(env, "type", "N/A")
                env_version = getattr(env, "dbt_version", None) or "N/A"
                lines.append(f"##### (ENV ID: {env_id}) **{env_name}** — Type: `{env_type}` — Version: `{env_version}`")

                # Jobs under this environment
                env_jobs = [job for job in project.jobs if job.environment_key == env.key]
                if env_jobs:
                    lines.append("")
                    lines.append(f"**{env_name} Jobs**")
                    lines.append("")
                    lines.append("| ID | Job Name | Type | Execute Steps |")
                    lines.append("|----|----------|------|---------------|")
                    for job in env_jobs:
                        job_name = getattr(job, "name", "Unnamed Job")
                        job_id = getattr(job, "id", "N/A")
                        
                        # Get job type from settings (more reliable than triggers)
                        job_settings = getattr(job, "settings", {})
                        job_type = job_settings.get("job_type", "other")
                        
                        # Get execute steps
                        execute_steps = getattr(job, "execute_steps", [])
                        if execute_steps:
                            steps_str = "<br>".join(f"`{step}`" for step in execute_steps)
                        else:
                            steps_str = "*None*"
                        
                        lines.append(f"| {job_id} | {job_name} | `{job_type}` | {steps_str} |")
                else:
                    lines.append("  ")
                    if env_type == "development":
                        lines.append(f"  - *No jobs configured. Development environment.*")
                    else:
                        lines.append(f"  - *No jobs configured.*")
                
                lines.append("")
            
            lines.append("")

        lines.append("")

    return "\n".join(lines)


def write_reports(snapshot: AccountSnapshot, output_dir: Path) -> tuple[Path, Path]:
    """Write both summary and detailed reports to timestamped markdown files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    account_id = snapshot.account_id

    summary_path = output_dir / f"account_{account_id}_summary__{timestamp}.md"
    detailed_path = output_dir / f"account_{account_id}_outline__{timestamp}.md"

    summary_path.write_text(generate_summary_report(snapshot), encoding="utf-8")
    detailed_path.write_text(generate_detailed_outline(snapshot), encoding="utf-8")

    return summary_path, detailed_path

