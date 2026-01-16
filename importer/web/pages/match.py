"""Match step page - match source resources to existing target resources."""

import json
import logging
from pathlib import Path
from typing import Callable, Optional

from nicegui import ui

from importer.web.state import AppState, WorkflowStep, STEP_NAMES
from importer.web.components.target_matcher import (
    MatchSuggestion,
    generate_match_suggestions,
)
from importer.web.utils.mapping_file import (
    TargetResourceMapping,
    save_mapping_file,
    create_mapping_from_confirmations,
)
from importer.web.utils.yaml_viewer import create_yaml_viewer_dialog


# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_TEAL = "#047377"


def create_match_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the Match step page for source-to-target resource matching."""
    
    with ui.element("div").classes("w-full max-w-7xl mx-auto p-4").style(
        "display: grid; "
        "grid-template-rows: auto 1fr auto; "
        "height: calc(100vh - 100px); "
        "gap: 8px; "
        "overflow: hidden;"
    ):
        # Row 1: Header
        _create_header(state)
        
        # Check prerequisites
        if not state.map.normalize_complete:
            _create_prerequisite_message(
                "Source Scope Required",
                "Complete the Scope step to normalize source resources first.",
                "Go to Scope",
                WorkflowStep.SCOPE,
                on_step_change,
            )
            return
        
        if not state.target_fetch.fetch_complete:
            _create_prerequisite_message(
                "Target Fetch Required", 
                "Fetch the target account data to match existing resources.",
                "Go to Fetch Target",
                WorkflowStep.FETCH_TARGET,
                on_step_change,
            )
            return
        
        # Load source and target report items
        source_items = _load_report_items(state, target=False)
        target_items = _load_report_items(state, target=True)
        
        if not source_items:
            _create_no_data_message("No source data available", on_step_change)
            return
        
        if not target_items:
            _create_no_data_message("No target data available", on_step_change)
            return
        
        # Row 2: Main content
        with ui.element("div").style(
            "width: 100%; height: 100%; overflow: auto;"
        ):
            _create_matching_content(state, source_items, target_items, save_state)
        
        # Row 3: Navigation
        _create_navigation(state, on_step_change, save_state)


def _create_header(state: AppState) -> None:
    """Create the page header."""
    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-1"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("link", size="md").style(f"color: {DBT_TEAL};")
                    ui.label("Match Source to Target Resources").classes("text-2xl font-bold")
                
                ui.label(
                    "Match source resources to existing target resources for Terraform import"
                ).classes("text-slate-600 dark:text-slate-400")
            
            # Show both account names
            with ui.row().classes("gap-4"):
                if state.fetch.account_name:
                    with ui.card().classes("p-2"):
                        ui.label("Source").classes("text-xs text-slate-500")
                        ui.label(state.fetch.account_name).classes("font-medium text-sm")
                
                ui.icon("arrow_forward").classes("text-slate-400 self-center")
                
                if state.target_fetch.account_name:
                    with ui.card().classes("p-2").style(f"border: 1px solid {DBT_TEAL};"):
                        ui.label("Target").classes("text-xs text-slate-500")
                        ui.label(state.target_fetch.account_name).classes("font-medium text-sm")


def _create_prerequisite_message(
    title: str,
    message: str,
    button_text: str,
    target_step: WorkflowStep,
    on_step_change: Callable[[WorkflowStep], None],
) -> None:
    """Show message when prerequisites are not met."""
    with ui.card().classes("w-full p-8 text-center"):
        ui.icon("warning", size="3rem").classes("text-amber-500 mx-auto")
        ui.label(title).classes("text-xl font-bold mt-4")
        ui.label(message).classes("text-slate-600 dark:text-slate-400 mt-2")
        ui.button(
            button_text,
            icon="arrow_back",
            on_click=lambda: on_step_change(target_step),
        ).classes("mt-4").style(f"background-color: {DBT_TEAL};")


def _create_no_data_message(message: str, on_step_change: Callable[[WorkflowStep], None]) -> None:
    """Show message when data is missing."""
    with ui.card().classes("w-full p-8 text-center"):
        ui.icon("error_outline", size="3rem").classes("text-red-500 mx-auto")
        ui.label(message).classes("text-xl font-bold mt-4")


def _load_report_items(state: AppState, target: bool = False) -> list:
    """Load report items from source or target fetch."""
    if target:
        report_file = state.target_fetch.last_report_items_file
    else:
        report_file = state.fetch.last_report_items_file
    
    if not report_file:
        return []
    
    try:
        report_path = Path(report_file)
        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        logging.warning(f"Error loading report items: {e}")
    
    return []


def _create_matching_content(
    state: AppState,
    source_items: list,
    target_items: list,
    save_state: Callable[[], None],
) -> None:
    """Create the main matching interface."""
    
    # Generate suggestions if not already done
    if not state.map.suggested_matches:
        suggestions = generate_match_suggestions(source_items, target_items)
        state.map.suggested_matches = [
            {
                "source_name": s.source_name,
                "source_key": s.source_key,
                "source_type": s.source_type,
                "target_name": s.target_name,
                "target_id": s.target_id,
                "target_type": s.target_type,
                "confidence": s.confidence,
                "status": s.status,
            }
            for s in suggestions
        ]
        save_state()
    
    # Convert suggested_matches to MatchSuggestion objects
    suggestions = [
        MatchSuggestion(
            source_name=s["source_name"],
            source_key=s["source_key"],
            source_type=s["source_type"],
            target_name=s["target_name"],
            target_id=s["target_id"],
            target_type=s["target_type"],
            confidence=s.get("confidence", "exact_match"),
            status=s.get("status", "suggested"),
        )
        for s in state.map.suggested_matches
    ]
    
    # Stats summary
    pending = sum(1 for s in suggestions if s.status == "suggested")
    confirmed = len(state.map.confirmed_mappings)
    rejected = len(state.map.rejected_suggestions)
    
    with ui.row().classes("w-full gap-4 mb-4"):
        _create_stat_card("Pending", pending, "text-amber-600", "hourglass_empty")
        _create_stat_card("Confirmed", confirmed, "text-green-600", "check_circle")
        _create_stat_card("Rejected", rejected, "text-slate-500", "cancel")
        _create_stat_card("Source Items", len(source_items), "text-blue-600", "upload")
        _create_stat_card("Target Items", len(target_items), f"color: {DBT_TEAL}", "download")
    
    # Info banner
    with ui.card().classes("w-full p-3 mb-4").style(f"border-left: 4px solid {DBT_TEAL};"):
        with ui.row().classes("items-start gap-2"):
            ui.icon("info", size="sm").style(f"color: {DBT_TEAL};")
            with ui.column().classes("gap-1"):
                ui.label("How Matching Works").classes("font-semibold text-sm")
                ui.label(
                    "Resources are matched by exact name (case-sensitive). "
                    "Confirm matches to import existing target resources into Terraform state, "
                    "or reject them to create new resources instead."
                ).classes("text-xs text-slate-500")
    
    # Two-column layout: Pending on left, Confirmed on right
    with ui.row().classes("w-full gap-4"):
        # Left: Pending Suggestions
        with ui.card().classes("flex-1 p-4"):
            ui.label("Pending Suggestions").classes("text-lg font-semibold mb-3")
            
            if pending == 0:
                with ui.row().classes("items-center gap-2 p-4"):
                    ui.icon("check_circle", size="md").classes("text-green-500")
                    ui.label("All suggestions reviewed!").classes("text-slate-500")
            else:
                # Bulk actions
                with ui.row().classes("w-full gap-2 mb-3"):
                    def confirm_all():
                        for s in state.map.suggested_matches:
                            if s["status"] == "suggested":
                                state.map.confirmed_mappings.append({
                                    "resource_type": s["source_type"],
                                    "source_name": s["source_name"],
                                    "source_key": s["source_key"],
                                    "target_id": s["target_id"],
                                    "target_name": s["target_name"],
                                    "match_type": "auto",
                                })
                                s["status"] = "confirmed"
                        save_state()
                        ui.navigate.reload()
                    
                    def reject_all():
                        for s in state.map.suggested_matches:
                            if s["status"] == "suggested":
                                state.map.rejected_suggestions.add(s["source_key"])
                                s["status"] = "rejected"
                        save_state()
                        ui.navigate.reload()
                    
                    ui.button(
                        f"Confirm All ({pending})",
                        icon="check",
                        on_click=confirm_all,
                    ).props("size=sm color=positive outline")
                    
                    ui.button(
                        "Reject All",
                        icon="close",
                        on_click=reject_all,
                    ).props("size=sm color=negative outline")
                
                # Suggestions list
                with ui.element("div").style("max-height: 400px; overflow-y: auto;"):
                    for s in suggestions:
                        if s.status != "suggested":
                            continue
                        
                        with ui.card().classes("w-full p-3 mb-2"):
                            with ui.row().classes("w-full items-center justify-between"):
                                with ui.column().classes("gap-0 flex-1"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(s.source_type).classes("text-xs px-2 py-0.5 rounded bg-slate-200 dark:bg-slate-700")
                                        ui.label(s.source_name).classes("font-mono font-medium")
                                    
                                    with ui.row().classes("items-center gap-1 mt-1"):
                                        ui.icon("arrow_forward", size="xs").classes("text-slate-400")
                                        ui.label(f"{s.target_name} (ID: {s.target_id})").classes("text-xs text-slate-500")
                                
                                with ui.row().classes("gap-1"):
                                    def make_confirm(suggestion):
                                        def confirm():
                                            state.map.confirmed_mappings.append({
                                                "resource_type": suggestion.source_type,
                                                "source_name": suggestion.source_name,
                                                "source_key": suggestion.source_key,
                                                "target_id": suggestion.target_id,
                                                "target_name": suggestion.target_name,
                                                "match_type": "auto",
                                            })
                                            for m in state.map.suggested_matches:
                                                if m["source_key"] == suggestion.source_key:
                                                    m["status"] = "confirmed"
                                                    break
                                            save_state()
                                            ui.navigate.reload()
                                        return confirm
                                    
                                    def make_reject(suggestion):
                                        def reject():
                                            state.map.rejected_suggestions.add(suggestion.source_key)
                                            for m in state.map.suggested_matches:
                                                if m["source_key"] == suggestion.source_key:
                                                    m["status"] = "rejected"
                                                    break
                                            save_state()
                                            ui.navigate.reload()
                                        return reject
                                    
                                    ui.button(
                                        icon="check",
                                        on_click=make_confirm(s),
                                    ).props("size=sm color=positive flat round")
                                    ui.button(
                                        icon="close",
                                        on_click=make_reject(s),
                                    ).props("size=sm color=negative flat round")
        
        # Right: Confirmed Mappings
        with ui.card().classes("flex-1 p-4"):
            ui.label("Confirmed Mappings").classes("text-lg font-semibold mb-3")
            
            if not state.map.confirmed_mappings:
                with ui.row().classes("items-center gap-2 p-4"):
                    ui.icon("info", size="md").classes("text-slate-400")
                    ui.label("No confirmed mappings yet").classes("text-slate-500")
            else:
                with ui.element("div").style("max-height: 400px; overflow-y: auto;"):
                    for mapping in state.map.confirmed_mappings:
                        with ui.card().classes("w-full p-3 mb-2 border-l-2 border-green-500"):
                            with ui.row().classes("w-full items-center justify-between"):
                                with ui.column().classes("gap-0 flex-1"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(mapping.get("resource_type", "")).classes("text-xs px-2 py-0.5 rounded bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300")
                                        ui.label(mapping.get("source_name", "")).classes("font-mono font-medium")
                                    
                                    with ui.row().classes("items-center gap-1 mt-1"):
                                        ui.icon("arrow_forward", size="xs").classes("text-green-500")
                                        ui.label(f"{mapping.get('target_name', '')} (ID: {mapping.get('target_id', '')})").classes("text-xs text-slate-500")
                                
                                def make_remove(m):
                                    def remove():
                                        state.map.confirmed_mappings.remove(m)
                                        # Reset the suggestion status
                                        for s in state.map.suggested_matches:
                                            if s["source_key"] == m.get("source_key"):
                                                s["status"] = "suggested"
                                                break
                                        save_state()
                                        ui.navigate.reload()
                                    return remove
                                
                                ui.button(
                                    icon="delete",
                                    on_click=make_remove(mapping),
                                ).props("size=sm color=negative flat round")
    
    # Save mapping file section
    if state.map.confirmed_mappings:
        with ui.card().classes("w-full p-4 mt-4").style(f"border: 2px solid {DBT_TEAL};"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-1"):
                    ui.label("Save Mapping File").classes("font-semibold")
                    ui.label(
                        f"{len(state.map.confirmed_mappings)} confirmed mappings ready to save"
                    ).classes("text-sm text-slate-500")
                    
                    if state.map.mapping_file_path:
                        ui.label(f"Last saved: {state.map.mapping_file_path}").classes("text-xs text-green-600 mt-1")
                
                def save_mappings():
                    try:
                        mapping = create_mapping_from_confirmations(
                            state.map.confirmed_mappings,
                            state.source_account.account_id or "unknown",
                            state.target_account.account_id or "unknown",
                        )
                        
                        output_dir = Path(state.fetch.output_dir)
                        output_path = output_dir / "target_resource_mapping.yml"
                        
                        error = save_mapping_file(mapping, output_path)
                        if error:
                            ui.notify(f"Error saving: {error}", type="negative")
                        else:
                            state.map.mapping_file_path = str(output_path)
                            state.map.mapping_file_valid = True
                            save_state()
                            ui.notify(f"Mapping saved to {output_path}", type="positive")
                            # Reload to update navigation button state
                            ui.navigate.reload()
                            
                    except Exception as e:
                        ui.notify(f"Error: {e}", type="negative")
                
                def view_mapping_file():
                    if state.map.mapping_file_path and Path(state.map.mapping_file_path).exists():
                        dialog = create_yaml_viewer_dialog(
                            state.map.mapping_file_path,
                            title="Target Resource Mapping"
                        )
                        dialog.open()
                    else:
                        ui.notify("Mapping file not found. Save the mapping first.", type="warning")
                
                with ui.row().classes("gap-2"):
                    ui.button(
                        "Save Mapping File",
                        icon="save",
                        on_click=save_mappings,
                    ).style(f"background-color: {DBT_TEAL};")
                    
                    if state.map.mapping_file_path:
                        ui.button(
                            "View Mapping",
                            icon="visibility",
                            on_click=view_mapping_file,
                        ).props("outline")


def _create_stat_card(label: str, value: int, color_class: str, icon_name: str) -> None:
    """Create a stat card."""
    with ui.card().classes("p-3 min-w-[120px]"):
        with ui.row().classes("items-center gap-2"):
            ui.icon(icon_name, size="sm").classes(color_class)
            ui.label(str(value)).classes(f"text-2xl font-bold {color_class}")
        ui.label(label).classes("text-xs text-slate-500")


def _create_navigation(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create navigation buttons."""
    with ui.row().classes("w-full justify-between mt-4"):
        ui.button(
            f"Back to {state.get_step_label(WorkflowStep.EXPLORE_TARGET)}",
            icon="arrow_back",
            on_click=lambda: on_step_change(WorkflowStep.EXPLORE_TARGET),
        ).props("outline")
        
        # Show mapping status and continue button
        with ui.row().classes("items-center gap-4"):
            if state.map.mapping_file_valid:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", size="sm").classes("text-green-500")
                    ui.label("Mapping saved").classes("text-green-600 text-sm")
            elif state.map.confirmed_mappings:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("warning", size="sm").classes("text-amber-500")
                    ui.label("Save mapping file to continue").classes("text-amber-600 text-sm")
            
            continue_enabled = state.map.mapping_file_valid or not state.map.confirmed_mappings
            
            btn = ui.button(
                f"Continue to {state.get_step_label(WorkflowStep.CONFIGURE)}",
                icon="arrow_forward",
                on_click=lambda: on_step_change(WorkflowStep.CONFIGURE),
            ).style(f"background-color: {DBT_ORANGE};")
            
            if not continue_enabled:
                btn.disable()
