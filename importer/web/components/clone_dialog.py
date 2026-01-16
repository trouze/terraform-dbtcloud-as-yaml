"""Clone resource configuration dialog component."""

from typing import Callable, Optional
import yaml

from nicegui import ui

from importer.web.state import AppState, CloneConfig
from importer.web.utils.dependency_analyzer import (
    get_children_by_type,
    get_required_dependencies,
    validate_clone_dependencies,
)


# Colors
DBT_ORANGE = "#FF694A"
DBT_TEAL = "#047377"

# Resource type display names
TYPE_NAMES = {
    "ACC": "Account",
    "CON": "Connection",
    "REP": "Repository",
    "TOK": "Service Token",
    "GRP": "Group",
    "NOT": "Notification",
    "WEB": "Webhook",
    "PLE": "PrivateLink",
    "PRJ": "Project",
    "ENV": "Environment",
    "VAR": "Environment Variable",
    "JOB": "Job",
}


def show_clone_dialog(
    source_item: dict,
    all_source_items: list[dict],
    state: AppState,
    on_save: Callable[[CloneConfig], None],
    existing_config: Optional[CloneConfig] = None,
) -> None:
    """Show the clone configuration dialog.
    
    Args:
        source_item: The source resource item being cloned
        all_source_items: All source account report items
        state: Application state
        on_save: Callback when clone config is saved
        existing_config: Existing config to edit (if any)
    """
    source_key = source_item.get("key", "")
    source_name = source_item.get("name", "")
    source_type = source_item.get("element_type_code", "")
    source_id = source_item.get("dbt_id", "")
    
    type_name = TYPE_NAMES.get(source_type, source_type)
    
    # Get children and required dependencies
    children_by_type = get_children_by_type(source_key, all_source_items)
    required_deps = get_required_dependencies(source_item, all_source_items)
    required_keys = {d.get("key") for d in required_deps if d.get("key")}
    
    # Initialize state from existing config or defaults
    new_name = existing_config.new_name if existing_config else f"{source_name} - Copy"
    selected_deps = set(existing_config.include_dependents) if existing_config else set()
    dep_names = dict(existing_config.dependent_names) if existing_config else {}
    include_env_values = existing_config.include_env_values if existing_config else True
    include_triggers = existing_config.include_triggers if existing_config else False
    include_credentials = existing_config.include_credentials if existing_config else False
    
    # Track state in mutable container
    dialog_state = {
        "new_name": new_name,
        "selected_deps": selected_deps,
        "dep_names": dep_names,
        "include_env_values": include_env_values,
        "include_triggers": include_triggers,
        "include_credentials": include_credentials,
    }
    
    with ui.dialog() as dialog, ui.card().classes("w-[700px] max-h-[80vh]"):
        # Header
        with ui.row().classes("w-full items-center justify-between mb-4"):
            with ui.column().classes("gap-1"):
                ui.label("Clone Resource").classes("text-xl font-bold")
                with ui.row().classes("items-center gap-2"):
                    ui.label(f"{type_name}:").classes("text-sm text-slate-500")
                    ui.label(source_name).classes("text-sm font-medium")
                    ui.label(f"(ID: {source_id})").classes("text-xs text-slate-400 font-mono")
            
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")
        
        ui.separator()
        
        # Main content with scroll
        with ui.scroll_area().classes("w-full").style("max-height: 400px;"):
            # New Name section
            with ui.card().classes("w-full p-4 mb-3").style("background: #f8fafc;"):
                ui.label("Clone Name").classes("text-sm font-semibold mb-2")
                name_input = ui.input(
                    value=dialog_state["new_name"],
                    placeholder=f"Enter name for the cloned {type_name.lower()}",
                ).classes("w-full")
                
                def update_name(e):
                    dialog_state["new_name"] = e.value
                
                name_input.on("update:model-value", update_name)
            
            # Dependencies section
            if children_by_type or required_deps:
                with ui.card().classes("w-full p-4 mb-3"):
                    with ui.row().classes("items-center justify-between mb-3"):
                        ui.label("Include Dependencies").classes("text-sm font-semibold")
                        
                        def select_all_deps():
                            all_keys = set()
                            for items in children_by_type.values():
                                for item in items:
                                    key = item.get("key")
                                    if key:
                                        all_keys.add(key)
                            dialog_state["selected_deps"] = all_keys
                            dialog.update()
                        
                        ui.button(
                            "Select All",
                            icon="select_all",
                            on_click=select_all_deps,
                        ).props("flat dense size=sm")
                    
                    # Required dependencies
                    if required_deps:
                        with ui.expansion("Required Dependencies", icon="lock").classes("w-full mb-2"):
                            for dep in required_deps:
                                dep_key = dep.get("key", "")
                                dep_name = dep.get("name", "")
                                dep_type = dep.get("element_type_code", "")
                                reason = dep.get("_required_reason", "Required")
                                
                                with ui.row().classes("w-full items-center gap-2 py-1"):
                                    ui.checkbox(value=True).props("disable").classes("opacity-50")
                                    ui.label(f"{TYPE_NAMES.get(dep_type, dep_type)}: {dep_name}").classes("text-sm flex-1")
                                    ui.label(f"({reason})").classes("text-xs text-slate-500")
                                
                                # Always include required deps
                                dialog_state["selected_deps"].add(dep_key)
                    
                    # Children by type
                    for type_code, items in sorted(children_by_type.items()):
                        type_name_display = TYPE_NAMES.get(type_code, type_code)
                        count = len(items)
                        
                        with ui.expansion(
                            f"{type_name_display}s ({count})",
                            icon="folder_open",
                        ).classes("w-full mb-2"):
                            # Select all for this type
                            with ui.row().classes("w-full items-center justify-end mb-2"):
                                def make_select_type_handler(items_list):
                                    def handler():
                                        for item in items_list:
                                            key = item.get("key")
                                            if key:
                                                dialog_state["selected_deps"].add(key)
                                        dialog.update()
                                    return handler
                                
                                ui.button(
                                    "Select All",
                                    on_click=make_select_type_handler(items),
                                ).props("flat dense size=xs")
                            
                            for item in items:
                                item_key = item.get("key", "")
                                item_name = item.get("name", "")
                                is_required = item_key in required_keys
                                
                                with ui.row().classes("w-full items-center gap-2 py-1"):
                                    # Checkbox for selection
                                    def make_checkbox_handler(key):
                                        def handler(e):
                                            if e.value:
                                                dialog_state["selected_deps"].add(key)
                                            else:
                                                dialog_state["selected_deps"].discard(key)
                                        return handler
                                    
                                    cb = ui.checkbox(
                                        value=item_key in dialog_state["selected_deps"] or is_required,
                                        on_change=make_checkbox_handler(item_key),
                                    )
                                    if is_required:
                                        cb.props("disable")
                                    
                                    # Name with inline edit
                                    ui.label(item_name).classes("text-sm flex-1")
                                    
                                    # Custom name input
                                    with ui.row().classes("items-center gap-1"):
                                        ui.label("→").classes("text-slate-400")
                                        
                                        def make_name_handler(key):
                                            def handler(e):
                                                dialog_state["dep_names"][key] = e.value
                                            return handler
                                        
                                        current_name = dialog_state["dep_names"].get(item_key, f"{item_name} - Copy")
                                        name_field = ui.input(
                                            value=current_name,
                                            placeholder="New name...",
                                        ).props("dense outlined").classes("w-40")
                                        name_field.on("update:model-value", make_name_handler(item_key))
            
            # Advanced Options section
            with ui.expansion("Advanced Options", icon="settings").classes("w-full"):
                with ui.column().classes("w-full gap-3 py-2"):
                    # Environment values
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label("Include environment variable values").classes("text-sm")
                            ui.label(
                                "Copy the actual values of environment variables"
                            ).classes("text-xs text-slate-500")
                        
                        def update_env_values(e):
                            dialog_state["include_env_values"] = e.value
                        
                        ui.switch(
                            value=dialog_state["include_env_values"],
                            on_change=update_env_values,
                        )
                    
                    # Job triggers
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label("Include job triggers").classes("text-sm")
                            ui.label(
                                "Copy schedule and event triggers for jobs"
                            ).classes("text-xs text-slate-500")
                        
                        def update_triggers(e):
                            dialog_state["include_triggers"] = e.value
                        
                        ui.switch(
                            value=dialog_state["include_triggers"],
                            on_change=update_triggers,
                        )
                    
                    # Credentials
                    with ui.row().classes("w-full items-center justify-between"):
                        with ui.column().classes("gap-0"):
                            ui.label("Include connection credentials").classes("text-sm")
                            ui.label(
                                "⚠️ May include sensitive data"
                            ).classes("text-xs text-amber-600")
                        
                        def update_credentials(e):
                            dialog_state["include_credentials"] = e.value
                        
                        ui.switch(
                            value=dialog_state["include_credentials"],
                            on_change=update_credentials,
                        )
                    
                    # Warning banner for credentials
                    if dialog_state["include_credentials"]:
                        with ui.card().classes("w-full p-3").style("background: #FEF3C7;"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("warning", color="amber-700")
                                ui.label(
                                    "Credentials will be included in the clone. "
                                    "Review generated configuration carefully."
                                ).classes("text-sm text-amber-800")
        
        # Summary
        dep_count = len(dialog_state["selected_deps"])
        total_count = 1 + dep_count  # Source + deps
        
        with ui.row().classes("w-full items-center gap-2 my-3"):
            ui.icon("info", color="blue")
            summary_label = ui.label(
                f"Will create {total_count} new resource{'s' if total_count > 1 else ''}"
            ).classes("text-sm text-blue-700")
        
        ui.separator()
        
        # Footer buttons
        with ui.row().classes("w-full justify-between"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            
            with ui.row().classes("gap-2"):
                # Preview button
                async def show_preview():
                    config = CloneConfig(
                        source_key=source_key,
                        new_name=dialog_state["new_name"],
                        include_dependents=list(dialog_state["selected_deps"]),
                        dependent_names=dialog_state["dep_names"],
                        include_env_values=dialog_state["include_env_values"],
                        include_triggers=dialog_state["include_triggers"],
                        include_credentials=dialog_state["include_credentials"],
                    )
                    show_preview_dialog(config, source_item, all_source_items)
                
                ui.button(
                    "Preview YAML",
                    icon="preview",
                    on_click=show_preview,
                ).props("flat")
                
                # Save button
                def save_config():
                    # Validate name
                    if not dialog_state["new_name"].strip():
                        ui.notify("Clone name is required", type="negative")
                        return
                    
                    # Validate dependencies
                    errors = validate_clone_dependencies(
                        source_key,
                        dialog_state["selected_deps"],
                        all_source_items,
                    )
                    if errors:
                        for err in errors:
                            ui.notify(err, type="warning")
                        # Allow save anyway with warning
                    
                    config = CloneConfig(
                        source_key=source_key,
                        new_name=dialog_state["new_name"].strip(),
                        include_dependents=list(dialog_state["selected_deps"]),
                        dependent_names=dialog_state["dep_names"],
                        include_env_values=dialog_state["include_env_values"],
                        include_triggers=dialog_state["include_triggers"],
                        include_credentials=dialog_state["include_credentials"],
                    )
                    
                    on_save(config)
                    dialog.close()
                    ui.notify(f"Clone configured: {config.new_name}", type="positive")
                
                ui.button(
                    "Save Clone",
                    icon="save",
                    on_click=save_config,
                ).props("color=primary")
    
    dialog.open()


def show_preview_dialog(
    config: CloneConfig,
    source_item: dict,
    all_items: list[dict],
) -> None:
    """Show a preview of the generated clone configuration.
    
    Args:
        config: Clone configuration
        source_item: Source resource item
        all_items: All report items
    """
    # Build preview YAML
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    
    preview_data = {
        "clone_source": {
            "key": config.source_key,
            "original_name": source_item.get("name"),
            "new_name": config.new_name,
            "type": source_item.get("element_type_code"),
        },
        "options": {
            "include_env_values": config.include_env_values,
            "include_triggers": config.include_triggers,
            "include_credentials": config.include_credentials,
        },
        "dependents": [],
    }
    
    for dep_key in config.include_dependents:
        dep_item = items_by_key.get(dep_key)
        if dep_item:
            preview_data["dependents"].append({
                "key": dep_key,
                "original_name": dep_item.get("name"),
                "new_name": config.dependent_names.get(dep_key, f"{dep_item.get('name')} - Copy"),
                "type": dep_item.get("element_type_code"),
            })
    
    yaml_content = yaml.dump(preview_data, default_flow_style=False, sort_keys=False)
    
    with ui.dialog() as preview_dialog, ui.card().classes("w-[600px]"):
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.label("Clone Configuration Preview").classes("text-lg font-bold")
            ui.button(icon="close", on_click=preview_dialog.close).props("flat round dense")
        
        ui.separator()
        
        with ui.scroll_area().classes("w-full").style("max-height: 400px;"):
            ui.code(yaml_content, language="yaml").classes("w-full")
        
        ui.separator()
        
        with ui.row().classes("w-full justify-end gap-2"):
            async def copy_yaml():
                escaped = yaml_content.replace('`', '\\`')
                await ui.run_javascript(f'navigator.clipboard.writeText(`{escaped}`);')
                ui.notify("Copied to clipboard", type="positive")
            
            ui.button("Copy", icon="content_copy", on_click=copy_yaml).props("flat")
            ui.button("Close", on_click=preview_dialog.close).props("flat")
    
    preview_dialog.open()


def get_clone_config_for_key(
    source_key: str,
    cloned_resources: list[CloneConfig],
) -> Optional[CloneConfig]:
    """Get existing clone config for a source key.
    
    Args:
        source_key: The source resource key
        cloned_resources: List of clone configurations
        
    Returns:
        CloneConfig if found, None otherwise
    """
    for config in cloned_resources:
        if config.source_key == source_key:
            return config
    return None


def remove_clone_config(
    source_key: str,
    cloned_resources: list[CloneConfig],
) -> None:
    """Remove a clone config for a source key.
    
    Args:
        source_key: The source resource key
        cloned_resources: List of clone configurations (modified in place)
    """
    for i, config in enumerate(cloned_resources):
        if config.source_key == source_key:
            cloned_resources.pop(i)
            return
