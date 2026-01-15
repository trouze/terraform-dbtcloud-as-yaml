"""Destroy step page for selective resource taint/destroy."""

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Callable, Optional

from nicegui import ui

from importer.web.components.terminal_output import TerminalOutput
from importer.web.pages.deploy import _get_state_file_path, _get_terraform_env
from importer.web.state import AppState, WorkflowStep
from importer.web.utils.yaml_viewer import create_text_viewer_dialog


# dbt brand colors
DBT_ORANGE = "#FF694A"


def create_destroy_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the destroy step page content."""
    terminal = TerminalOutput(show_timestamps=True)

    destroy_state = {
        "terraform_dir": None,
        "selected": set(),
        "table": None,
    }

    with ui.column().classes("w-full max-w-6xl mx-auto p-6 gap-6"):
        with ui.row().classes("w-full items-center gap-4"):
            ui.icon("delete_forever", size="2rem").style(f"color: {DBT_ORANGE};")
            ui.label("Destroy Resources").classes("text-2xl font-bold")

        ui.label(
            "Inspect Terraform state and selectively taint or destroy resources."
        ).classes("text-slate-600 dark:text-slate-400")

        if not _check_prerequisites(state, on_step_change):
            return

        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("w-1/3 min-w-[260px] gap-4"):
                _create_state_inspection_panel(state, destroy_state)
                _create_bulk_actions_panel(state, terminal, save_state, destroy_state)

            with ui.column().classes("flex-grow gap-4"):
                _create_resource_table(state, destroy_state)
                with ui.card().classes("w-full"):
                    ui.label("Output").classes("font-semibold mb-2")
                    terminal.create(height="360px")

        _create_navigation_section(on_step_change)


def _check_prerequisites(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
) -> bool:
    """Check if prerequisites are met for destroy."""
    if not state.deploy.terraform_initialized:
        with ui.card().classes("w-full p-6 border-l-4 border-yellow-500"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("warning", size="lg").classes("text-yellow-500")
                ui.label("Prerequisites Required").classes("text-xl font-semibold")

            ui.label(
                "Initialize Terraform before running destroy actions."
            ).classes("mt-4 text-slate-600 dark:text-slate-400")

            ui.button(
                "Go to Deploy",
                icon="arrow_back",
                on_click=lambda: on_step_change(WorkflowStep.DEPLOY),
            ).props("outline size=sm").classes("mt-4")

        return False

    return True


def _create_state_inspection_panel(state: AppState, destroy_state: dict) -> None:
    """Create state inspection panel."""
    state_path = _get_state_file_path(state, destroy_state)

    def open_state_viewer() -> None:
        if not state_path:
            ui.notify("No terraform state file found", type="warning")
            return
        dialog = create_text_viewer_dialog(
            state_path,
            title="Terraform State",
            language="json",
        )
        dialog.open()

    with ui.card().classes("w-full"):
        ui.label("Inspect Terraform State").classes("font-semibold mb-2")
        if state_path:
            ui.label(state_path).classes("text-xs text-slate-500 font-mono truncate")
        else:
            ui.label("No state file available yet.").classes("text-xs text-slate-500")

        view_btn = ui.button(
            "View State",
            icon="visibility",
            on_click=open_state_viewer,
        ).props("outline")

        if not state_path:
            view_btn.disable()
            view_btn.tooltip("Generate, init, and apply to create state")


def _create_resource_table(state: AppState, destroy_state: dict) -> None:
    """Create the resource selection table."""
    resources = _load_state_resources(state, destroy_state)

    columns = [
        {"name": "address", "label": "Address", "field": "address", "align": "left"},
        {"name": "type", "label": "Type", "field": "type", "align": "left"},
        {"name": "name", "label": "Name", "field": "name", "align": "left"},
        {"name": "mode", "label": "Mode", "field": "mode", "align": "left"},
        {"name": "instances", "label": "Instances", "field": "instances", "align": "right"},
    ]

    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ui.label("Select Resources").classes("font-semibold")
            ui.button(
                "Refresh",
                icon="refresh",
                on_click=lambda: _refresh_resources(state, destroy_state),
            ).props("outline size=sm")

        table = ui.table(
            columns=columns,
            rows=resources,
            row_key="address",
        ).classes("w-full")
        table.props("selection=multiple")

        def on_selection(e) -> None:
            selected_rows = e.args.get("rows", [])
            destroy_state["selected"] = {row["address"] for row in selected_rows}

        table.on("selection", on_selection)
        destroy_state["table"] = table

        ui.label(
            "Select resources to taint or destroy using the actions on the left."
        ).classes("text-xs text-slate-500 mt-2")


def _create_bulk_actions_panel(
    state: AppState,
    terminal: TerminalOutput,
    save_state: Callable[[], None],
    destroy_state: dict,
) -> None:
    """Create bulk action buttons for taint/destroy."""
    with ui.card().classes("w-full"):
        ui.label("Actions").classes("font-semibold mb-2")

        with ui.row().classes("w-full gap-2 mb-3"):
            ui.button(
                "Select All",
                icon="select_all",
                on_click=lambda: _select_all(destroy_state),
            ).props("outline size=sm")
            ui.button(
                "Clear",
                icon="clear",
                on_click=lambda: _clear_selection(destroy_state),
            ).props("outline size=sm")

        ui.button(
            "Taint Selected",
            icon="warning",
            on_click=lambda: _run_terraform_taint(
                state, terminal, save_state, destroy_state
            ),
        ).classes("w-full").props("outline color=warning")

        ui.button(
            "Destroy Selected",
            icon="delete_forever",
            on_click=lambda: _confirm_destroy(
                state, terminal, save_state, destroy_state
            ),
        ).classes("w-full mt-2").props("outline color=negative")


def _select_all(destroy_state: dict) -> None:
    """Select all rows in the table."""
    table = destroy_state.get("table")
    if not table:
        return
    table.selected = list(table.rows)
    table.update()
    destroy_state["selected"] = {row["address"] for row in table.rows}


def _clear_selection(destroy_state: dict) -> None:
    """Clear all selections."""
    table = destroy_state.get("table")
    if not table:
        return
    table.selected = []
    table.update()
    destroy_state["selected"] = set()


def _refresh_resources(state: AppState, destroy_state: dict) -> None:
    """Reload resources from state file."""
    table = destroy_state.get("table")
    if not table:
        return
    table.rows = _load_state_resources(state, destroy_state)
    table.update()
    destroy_state["selected"] = set()


def _confirm_destroy(
    state: AppState,
    terminal: TerminalOutput,
    save_state: Callable[[], None],
    destroy_state: dict,
) -> None:
    """Confirm before destroy."""
    if not destroy_state["selected"]:
        ui.notify("Select resources first", type="warning")
        return

    with ui.dialog() as dialog:
        with ui.card().classes("w-full max-w-md"):
            ui.label("Confirm Destroy").classes("text-lg font-semibold")
            ui.label(
                "This will destroy the selected resources. This action cannot be undone."
            ).classes("text-sm text-slate-600 mt-2")
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("outline")
                def confirm_destroy() -> None:
                    dialog.close()
                    _run_terraform_destroy_selected(
                        state, terminal, save_state, destroy_state
                    )

                ui.button(
                    "Destroy",
                    on_click=confirm_destroy,
                ).props("color=negative")
    dialog.open()


def _load_state_resources(state: AppState, destroy_state: dict) -> list[dict]:
    """Load resources from terraform state file."""
    state_path = _get_state_file_path(state, destroy_state)
    if not state_path:
        return []

    try:
        content = Path(state_path).read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception:
        return []

    rows = []
    for resource in data.get("resources", []):
        address = resource.get("address")
        if not address:
            module = resource.get("module")
            address = ".".join(
                part for part in [module, resource.get("type"), resource.get("name")] if part
            )
        rows.append(
            {
                "address": address,
                "type": resource.get("type", ""),
                "name": resource.get("name", ""),
                "mode": resource.get("mode", ""),
                "instances": len(resource.get("instances", [])),
            }
        )

    return rows


async def _run_terraform_taint(
    state: AppState,
    terminal: TerminalOutput,
    save_state: Callable[[], None],
    destroy_state: dict,
) -> None:
    """Run terraform taint for selected resources."""
    selected = sorted(destroy_state.get("selected", []))
    if not selected:
        ui.notify("Select resources first", type="warning")
        return

    tf_dir = state.deploy.terraform_dir or "deployments/migration"

    terminal.clear()
    terminal.warning("━━━ TERRAFORM TAINT ━━━")
    terminal.info("")

    env = _get_terraform_env(state)

    for address in selected:
        terminal.info(f"Tainting {address}...")
        result = await asyncio.to_thread(
            subprocess.run,
            ["terraform", "taint", "-no-color", address],
            cwd=tf_dir,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode == 0:
            terminal.success(f"Tainted {address}")
        else:
            terminal.error(f"Failed to taint {address}")
            if result.stderr:
                terminal.warning(result.stderr.strip())

    ui.notify("Taint operations complete", type="positive")
    save_state()


async def _run_terraform_destroy_selected(
    state: AppState,
    terminal: TerminalOutput,
    save_state: Callable[[], None],
    destroy_state: dict,
) -> None:
    """Run terraform destroy for selected resources."""
    selected = sorted(destroy_state.get("selected", []))
    if not selected:
        ui.notify("Select resources first", type="warning")
        return

    tf_dir = state.deploy.terraform_dir or "deployments/migration"

    terminal.clear()
    terminal.warning("━━━ TERRAFORM DESTROY (SELECTED) ━━━")
    terminal.warning("")
    terminal.warning(f"Targets: {', '.join(selected)}")
    terminal.info("")

    env = _get_terraform_env(state)
    target_args = [f"-target={address}" for address in selected]

    result = await asyncio.to_thread(
        subprocess.run,
        ["terraform", "destroy", "-no-color", "-auto-approve", *target_args],
        cwd=tf_dir,
        capture_output=True,
        text=True,
        env=env,
    )

    for line in result.stdout.split("\n"):
        if line.strip():
            terminal.info(line)
    for line in result.stderr.split("\n"):
        if line.strip():
            terminal.warning(line)

    if result.returncode == 0:
        terminal.success("Destroy complete!")
        state.deploy.destroy_complete = True
        save_state()
        ui.notify("Destroy complete", type="positive")
    else:
        terminal.error(f"Destroy failed with exit code {result.returncode}")
        ui.notify("Destroy failed", type="negative")


def _create_navigation_section(on_step_change: Callable[[WorkflowStep], None]) -> None:
    """Create the navigation buttons section."""
    with ui.row().classes("w-full justify-between mt-6"):
        ui.button(
            "Back to Deploy",
            icon="arrow_back",
            on_click=lambda: on_step_change(WorkflowStep.DEPLOY),
        ).props("outline")
