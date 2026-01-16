"""Mapping table component for Jobs as Code Generator clone workflow."""

from typing import Callable, Optional

from nicegui import ui

from importer.web.state import JACProjectMapping, JACEnvironmentMapping


# dbt brand colors
DBT_ORANGE = "#FF694A"


def create_mapping_table(
    title: str,
    source_items: list[dict],
    target_items: list[dict],
    mappings: list,
    on_mapping_change: Callable[[int, Optional[int]], None],
    source_label: str = "Source",
    target_label: str = "Target",
) -> ui.element:
    """Create a generic mapping table for source -> target mappings.
    
    Args:
        title: Table title
        source_items: List of source items with 'id' and 'name' keys
        target_items: List of target items with 'id' and 'name' keys
        mappings: Current mappings (JACProjectMapping or JACEnvironmentMapping)
        on_mapping_change: Callback when mapping changes (source_id, target_id)
        source_label: Label for source column
        target_label: Label for target column
        
    Returns:
        The container element
    """
    with ui.card().classes("w-full") as card:
        ui.label(title).classes("text-lg font-semibold mb-4")
        
        # Build target options
        target_options = {"": "-- Select --"}
        for item in target_items:
            target_options[str(item["id"])] = f"{item['name']} ({item['id']})"
        
        # Build mapping lookup
        mapping_lookup = {}
        for m in mappings:
            if hasattr(m, "source_id"):
                mapping_lookup[m.source_id] = m.target_id
            else:
                mapping_lookup[m.get("source_id")] = m.get("target_id")
        
        # Create table
        with ui.column().classes("w-full gap-2"):
            # Header
            with ui.row().classes("w-full items-center gap-4 py-2 border-b"):
                ui.label(source_label).classes("w-1/3 font-semibold")
                ui.label("").classes("w-[40px]")  # Arrow space
                ui.label(target_label).classes("flex-grow font-semibold")
            
            # Rows
            for source in source_items:
                source_id = source["id"]
                source_name = source["name"]
                
                current_target = mapping_lookup.get(source_id)
                
                with ui.row().classes("w-full items-center gap-4 py-2"):
                    # Source info
                    with ui.column().classes("w-1/3"):
                        ui.label(source_name).classes("font-medium")
                        ui.label(f"ID: {source_id}").classes("text-xs text-slate-500")
                    
                    # Arrow
                    ui.icon("arrow_forward", size="sm").classes("text-slate-400")
                    
                    # Target selector
                    def make_change_handler(sid: int):
                        def handler(e):
                            target_id = int(e.args) if e.args else None
                            on_mapping_change(sid, target_id)
                        return handler
                    
                    select = ui.select(
                        options=target_options,
                        value=str(current_target) if current_target else "",
                    ).classes("flex-grow").props("outlined dense")
                    
                    select.on("update:model-value", make_change_handler(source_id))
        
        # Summary
        mapped_count = sum(1 for v in mapping_lookup.values() if v is not None)
        total_count = len(source_items)
        
        with ui.row().classes("w-full items-center gap-2 mt-4 pt-4 border-t"):
            if mapped_count == total_count:
                ui.icon("check_circle", size="sm").classes("text-green-500")
                ui.label(f"All {total_count} items mapped").classes("text-green-600")
            else:
                ui.icon("warning", size="sm").classes("text-amber-500")
                ui.label(f"{mapped_count} of {total_count} items mapped").classes(
                    "text-amber-600"
                )
    
    return card


def create_project_mapping_table(
    source_projects: dict[int, str],
    target_projects: dict[int, str],
    project_mappings: list[JACProjectMapping],
    on_mapping_change: Callable[[int, Optional[int]], None],
) -> ui.element:
    """Create a project mapping table.
    
    Args:
        source_projects: Dict of source project_id -> name
        target_projects: Dict of target project_id -> name
        project_mappings: Current project mappings
        on_mapping_change: Callback when mapping changes
        
    Returns:
        The container element
    """
    source_items = [{"id": k, "name": v} for k, v in source_projects.items()]
    target_items = [{"id": k, "name": v} for k, v in target_projects.items()]
    
    return create_mapping_table(
        title="Project Mapping",
        source_items=source_items,
        target_items=target_items,
        mappings=project_mappings,
        on_mapping_change=on_mapping_change,
        source_label="Source Project",
        target_label="Target Project",
    )


def create_environment_mapping_table(
    source_environments: dict[int, dict],
    target_environments: dict[int, dict],
    environment_mappings: list[JACEnvironmentMapping],
    on_mapping_change: Callable[[int, Optional[int]], None],
    source_project_filter: Optional[int] = None,
) -> ui.element:
    """Create an environment mapping table.
    
    Args:
        source_environments: Dict of source env_id -> env info dict
        target_environments: Dict of target env_id -> env info dict
        environment_mappings: Current environment mappings
        on_mapping_change: Callback when mapping changes
        source_project_filter: Optional project ID to filter source envs
        
    Returns:
        The container element
    """
    # Build source items
    source_items = []
    for env_id, env_info in source_environments.items():
        if source_project_filter and env_info.get("project_id") != source_project_filter:
            continue
        source_items.append({
            "id": env_id,
            "name": env_info.get("name", f"Environment {env_id}"),
        })
    
    # Build target items
    target_items = [
        {"id": k, "name": v.get("name", f"Environment {k}")}
        for k, v in target_environments.items()
    ]
    
    return create_mapping_table(
        title="Environment Mapping",
        source_items=source_items,
        target_items=target_items,
        mappings=environment_mappings,
        on_mapping_change=on_mapping_change,
        source_label="Source Environment",
        target_label="Target Environment",
    )


def create_auto_match_button(
    source_items: list[dict],
    target_items: list[dict],
    on_auto_match: Callable[[dict[int, int]], None],
) -> ui.element:
    """Create an auto-match button that suggests mappings by name.
    
    Args:
        source_items: List of source items
        target_items: List of target items
        on_auto_match: Callback with suggested mappings (source_id -> target_id)
        
    Returns:
        Button element
    """
    def do_auto_match():
        # Build target name lookup
        target_by_name: dict[str, int] = {}
        for item in target_items:
            name_lower = item["name"].lower().strip()
            target_by_name[name_lower] = item["id"]
        
        # Match by name
        matches: dict[int, int] = {}
        for source in source_items:
            source_name = source["name"].lower().strip()
            if source_name in target_by_name:
                matches[source["id"]] = target_by_name[source_name]
        
        if matches:
            on_auto_match(matches)
            ui.notify(f"Auto-matched {len(matches)} items by name", type="positive")
        else:
            ui.notify("No matches found by name", type="warning")
    
    return ui.button(
        "Auto-Match by Name",
        icon="auto_fix_high",
        on_click=do_auto_match,
    ).props("outline")


def create_mapping_summary(
    project_mappings: list[JACProjectMapping],
    environment_mappings: list[JACEnvironmentMapping],
    total_projects: int,
    total_environments: int,
) -> ui.element:
    """Create a summary of mapping completion status.
    
    Args:
        project_mappings: Current project mappings
        environment_mappings: Current environment mappings
        total_projects: Total number of source projects
        total_environments: Total number of source environments
        
    Returns:
        The container element
    """
    projects_mapped = sum(1 for m in project_mappings if m.target_id is not None)
    envs_mapped = sum(1 for m in environment_mappings if m.target_id is not None)
    
    all_mapped = (projects_mapped == total_projects and envs_mapped == total_environments)
    
    with ui.card().classes("w-full") as card:
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Mapping Status").classes("text-lg font-semibold")
            
            if all_mapped:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", size="md").classes("text-green-500")
                    ui.label("All mappings complete").classes("text-green-600 font-medium")
            else:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("pending", size="md").classes("text-amber-500")
                    ui.label("Mappings incomplete").classes("text-amber-600 font-medium")
        
        with ui.row().classes("gap-8 mt-4"):
            # Projects
            with ui.column().classes("items-center"):
                ui.label(f"{projects_mapped}/{total_projects}").classes("text-2xl font-bold")
                ui.label("Projects").classes("text-sm text-slate-500")
            
            # Environments
            with ui.column().classes("items-center"):
                ui.label(f"{envs_mapped}/{total_environments}").classes("text-2xl font-bold")
                ui.label("Environments").classes("text-sm text-slate-500")
    
    return card
