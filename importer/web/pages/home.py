"""Home/dashboard page for the web UI."""

import json
from pathlib import Path
from typing import Callable, Optional

from nicegui import ui

from importer.web.state import AppState, WorkflowStep, WorkflowType, WORKFLOW_LABELS


def create_home_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    on_workflow_change: Callable[[WorkflowType], None],
) -> None:
    """Create the home/dashboard page content.

    Args:
        state: Current application state
        on_step_change: Callback to navigate to a step
        on_workflow_change: Callback to switch workflows
    """
    with ui.column().classes("w-full max-w-4xl mx-auto p-8 gap-8"):
        # Welcome section
        _create_welcome_section(state, on_step_change, on_workflow_change)

        # Quick stats (if there's previous data)
        if state.fetch.fetch_complete:
            _create_quick_stats(state)

        # Recent runs
        _create_recent_runs_section(state, on_step_change)


def _create_welcome_section(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    on_workflow_change: Callable[[WorkflowType], None],
) -> None:
    """Create the welcome/hero section."""
    with ui.card().classes("w-full p-6"):
        with ui.column().classes("gap-3"):
            ui.markdown("""
                Choose a workflow to explore, audit, or migrate dbt Platform account configurations.
            """).classes("text-slate-600 dark:text-slate-400")

            with ui.row().classes("gap-4 mt-4 flex-wrap"):
                _create_workflow_card(
                    title=WORKFLOW_LABELS[WorkflowType.MIGRATION],
                    description="Full end-to-end migration with scoped selection and deploy.",
                    icon="rocket_launch",
                    on_click=lambda: on_workflow_change(WorkflowType.MIGRATION),
                    highlight=True,
                )
                _create_workflow_card(
                    title=WORKFLOW_LABELS[WorkflowType.ACCOUNT_EXPLORER],
                    description="Fetch and explore account configuration without deployment.",
                    icon="search",
                    on_click=lambda: on_workflow_change(WorkflowType.ACCOUNT_EXPLORER),
                )
                _create_workflow_card(
                    title=WORKFLOW_LABELS[WorkflowType.JOBS_AS_CODE],
                    description="Generate jobs-as-code outputs from selected entities.",
                    icon="code",
                    on_click=lambda: on_workflow_change(WorkflowType.JOBS_AS_CODE),
                )
                _create_workflow_card(
                    title=WORKFLOW_LABELS[WorkflowType.IMPORT_ADOPT],
                    description="Import existing infrastructure and adopt it into Terraform.",
                    icon="cloud_sync",
                    on_click=None,
                    disabled=True,
                )

            with ui.row().classes("gap-4 mt-4"):
                ui.button(
                    "Documentation",
                    icon="menu_book",
                    on_click=lambda: ui.notify("Documentation coming soon"),
                ).props("outline")


def _create_workflow_card(
    title: str,
    description: str,
    icon: str,
    on_click: Optional[Callable[[], None]],
    highlight: bool = False,
    disabled: bool = False,
) -> None:
    """Create a workflow selection card."""
    card_classes = "w-full md:w-[calc(50%-0.5rem)] p-4"
    if highlight:
        card_classes += " border-2 border-orange-400"

    with ui.card().classes(card_classes):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon, size="md").classes("text-slate-400")
            ui.label(title).classes("text-lg font-semibold")
            if disabled:
                ui.badge("Coming Soon", color="warning").props("rounded")

        ui.label(description).classes("text-sm text-slate-500 mt-2")

        action = ui.button(
            "Select",
            icon="arrow_forward",
            on_click=on_click if on_click else None,
        ).props("outline")
        if disabled:
            action.disable()


def _create_quick_stats(state: AppState) -> None:
    """Create quick stats cards from the last fetch."""
    with ui.card().classes("w-full"):
        ui.label("Current Session").classes("text-lg font-semibold mb-4")

        with ui.row().classes("gap-4 flex-wrap"):
            # Account info
            if state.fetch.account_name:
                _stat_card("Account", state.fetch.account_name, "business")

            # Resource counts
            counts = state.fetch.resource_counts
            if counts:
                if "projects" in counts:
                    _stat_card("Projects", str(counts["projects"]), "folder")
                if "environments" in counts:
                    _stat_card("Environments", str(counts["environments"]), "dns")
                if "jobs" in counts:
                    _stat_card("Jobs", str(counts["jobs"]), "schedule")
                if "connections" in counts:
                    _stat_card("Connections", str(counts["connections"]), "cable")


def _stat_card(label: str, value: str, icon: str) -> None:
    """Create a small stat card."""
    with ui.card().classes("p-4 min-w-[120px]"):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon, size="sm").style("color: #FF694A;")
            ui.label(label).classes("text-sm text-slate-500")
        ui.label(value).classes("text-xl font-semibold mt-1")


def _create_recent_runs_section(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
) -> None:
    """Create the recent runs table."""
    with ui.card().classes("w-full"):
        ui.label("Recent Runs").classes("text-lg font-semibold mb-4")

        # Try to load recent runs
        runs = _load_recent_runs(state.fetch.output_dir)

        if not runs:
            with ui.row().classes("items-center gap-2 text-slate-500"):
                ui.icon("info", size="sm")
                ui.label("No previous runs found. Click 'Get Started' to fetch your first account.")
            return

        # Create table
        columns = [
            {"name": "type", "label": "Type", "field": "type", "align": "left"},
            {"name": "account", "label": "Account", "field": "account", "align": "left"},
            {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
            {"name": "status", "label": "Status", "field": "status", "align": "left"},
            {"name": "actions", "label": "", "field": "actions", "align": "center"},
        ]

        rows = []
        for run in runs[:10]:  # Show last 10
            rows.append({
                "type": run.get("type", "fetch"),
                "account": f"Account {run.get('account_id', 'N/A')}",
                "timestamp": run.get("timestamp", "Unknown"),
                "status": "Complete" if run.get("success", True) else "Failed",
                "run_id": run.get("run_id", ""),
                "account_id": run.get("account_id", ""),
                "run_type": run.get("type", "fetch"),
            })

        table = ui.table(columns=columns, rows=rows, row_key="timestamp").classes("w-full")
        table.add_slot(
            "body-cell-actions",
            '''
            <q-td :props="props">
                <q-btn flat dense icon="open_in_new" size="sm" @click="$parent.$emit('load-run', props.row)" />
            </q-td>
            '''
        )
        table.on("load-run", lambda e: _load_run_and_navigate(
            e.args, state, on_step_change
        ))

        ui.label("Click a row to load that run's data into the Explore view.").classes(
            "text-xs text-slate-500 mt-2"
        )


def _load_run_and_navigate(
    row: dict,
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
) -> None:
    """Load a run's data and navigate to Explore.
    
    Args:
        row: Table row data containing run information
        state: Application state to update
        on_step_change: Callback to navigate
    """
    account_id = row.get("account_id", "")
    run_id = row.get("run_id", "")
    run_type = row.get("run_type", "fetch")
    
    if not account_id or not run_id:
        ui.notify("Run data not available", type="warning")
        return
    
    output_path = Path(state.fetch.output_dir)
    
    # Find the YAML file for this run
    yaml_file = None
    
    if run_type == "fetch":
        # Look for the fetched account YAML
        account_yaml = output_path / str(account_id) / run_id / f"account_{account_id}.yaml"
        if account_yaml.exists():
            yaml_file = account_yaml
        else:
            # Try alternative path patterns
            account_dir = output_path / str(account_id) / run_id
            if account_dir.exists():
                yaml_files = list(account_dir.glob("*.yaml"))
                if yaml_files:
                    yaml_file = yaml_files[0]
    elif run_type == "normalize":
        # Look for normalized YAML
        norm_yaml = output_path / "normalized" / str(account_id) / run_id / "normalized.yaml"
        if norm_yaml.exists():
            yaml_file = norm_yaml
    
    if not yaml_file or not yaml_file.exists():
        ui.notify(f"Could not find data for run {run_id}", type="warning")
        return
    
    # Update state
    state.fetch.fetch_complete = True
    state.fetch.last_yaml_file = str(yaml_file)
    state.source_account.account_id = account_id
    
    ui.notify(f"Loaded run {run_id}", type="positive")
    
    # Navigate to Explore
    on_step_change(WorkflowStep.EXPLORE_SOURCE)


def _load_recent_runs(output_dir: str) -> list:
    """Load recent runs from importer_runs.json and normalization_runs.json."""
    runs = []

    # Try to find runs files
    output_path = Path(output_dir)
    if not output_path.exists():
        return runs

    # Load fetch runs
    importer_runs_file = output_path / "importer_runs.json"
    if importer_runs_file.exists():
        try:
            data = json.loads(importer_runs_file.read_text())
            for account_id, account_runs in data.items():
                for run in account_runs:
                    runs.append({
                        "type": "fetch",
                        "account_id": account_id,
                        "timestamp": run.get("timestamp", ""),
                        "run_id": run.get("run_id"),
                        "success": True,
                    })
        except (json.JSONDecodeError, KeyError):
            pass

    # Load normalize runs
    norm_dir = output_path / "normalized"
    norm_runs_file = norm_dir / "normalization_runs.json"
    if norm_runs_file.exists():
        try:
            data = json.loads(norm_runs_file.read_text())
            for account_id, account_runs in data.items():
                for run in account_runs:
                    runs.append({
                        "type": "normalize",
                        "account_id": account_id,
                        "timestamp": run.get("timestamp", ""),
                        "run_id": run.get("norm_run_id"),
                        "success": True,
                    })
        except (json.JSONDecodeError, KeyError):
            pass

    # Sort by timestamp descending
    runs.sort(key=lambda r: r.get("timestamp", ""), reverse=True)

    return runs
