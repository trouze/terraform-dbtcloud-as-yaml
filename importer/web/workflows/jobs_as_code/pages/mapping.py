"""Resource mapping page for Jobs as Code Generator clone workflow."""

from typing import Callable

from nicegui import ui

from importer.web.state import (
    AppState, WorkflowStep, JACProjectMapping, JACEnvironmentMapping
)


# dbt brand colors
DBT_ORANGE = "#FF694A"


def create_jac_mapping_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the resource mapping page.
    
    For clone workflow: Users map source projects/environments to target ones.
    
    Args:
        state: Application state
        on_step_change: Callback to navigate to a step
        save_state: Callback to save state
    """
    jac = state.jobs_as_code
    
    # Initialize mappings if needed
    if not jac.project_mappings:
        _initialize_mappings(jac)
    
    with ui.column().classes("w-full max-w-5xl mx-auto p-8 gap-6"):
        # Header
        with ui.card().classes("w-full p-6"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.icon("swap_horiz", size="lg").style(f"color: {DBT_ORANGE};")
                ui.label("Map Source to Target").classes("text-2xl font-bold")
            
            ui.badge("Clone / Migrate Jobs", color="orange").props("outline")
            
            ui.markdown("""
                Map source projects and environments to their target equivalents.
                The system will use these mappings when generating YAML for cloned jobs.
            """).classes("text-slate-600 dark:text-slate-400 mt-3")
        
        # Mapping summary
        _create_mapping_summary(jac)
        
        # Project mappings
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between mb-4"):
                ui.label("Project Mapping").classes("text-lg font-semibold")
                
                def auto_match_projects():
                    _auto_match_by_name(
                        jac.project_mappings,
                        jac.source_projects,
                        jac.target_projects,
                        is_project=True,
                    )
                    save_state()
                    ui.navigate.reload()
                
                ui.button(
                    "Auto-Match by Name",
                    icon="auto_fix_high",
                    on_click=auto_match_projects,
                ).props("outline size=sm")
            
            _create_project_mapping_table(jac, save_state)
        
        # Environment mappings
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between mb-4"):
                ui.label("Environment Mapping").classes("text-lg font-semibold")
                
                def auto_match_environments():
                    _auto_match_by_name(
                        jac.environment_mappings,
                        {k: v.get("name", f"Env {k}") for k, v in jac.source_environments.items()},
                        {k: v.get("name", f"Env {k}") for k, v in jac.target_environments.items()},
                        is_project=False,
                    )
                    save_state()
                    ui.navigate.reload()
                
                ui.button(
                    "Auto-Match by Name",
                    icon="auto_fix_high",
                    on_click=auto_match_environments,
                ).props("outline size=sm")
            
            _create_environment_mapping_table(jac, save_state)
        
        # Navigation
        with ui.row().classes("w-full justify-between items-center mt-4"):
            ui.button(
                "Back",
                icon="arrow_back",
                on_click=lambda: on_step_change(WorkflowStep.JAC_TARGET),
            ).props("outline")
            
            # Check if mappings are complete
            projects_complete = all(m.target_id is not None for m in jac.project_mappings)
            envs_complete = all(m.target_id is not None for m in jac.environment_mappings)
            
            continue_btn = ui.button(
                "Configure Jobs",
                icon="arrow_forward",
                on_click=lambda: on_step_change(WorkflowStep.JAC_CONFIG),
            ).props("size=lg").style(f"background-color: {DBT_ORANGE};")
            
            if not (projects_complete and envs_complete):
                continue_btn.disable()
                ui.notify("Please complete all mappings before continuing", type="warning")


def _initialize_mappings(jac) -> None:
    """Initialize project and environment mappings."""
    # Get unique projects and environments from selected jobs
    selected_project_ids = set()
    selected_env_ids = set()
    
    jobs_by_id = {job.get("id"): job for job in jac.source_jobs}
    
    for job_id in jac.selected_job_ids:
        job = jobs_by_id.get(job_id)
        if job:
            selected_project_ids.add(job.get("project_id"))
            selected_env_ids.add(job.get("environment_id"))
    
    # Create project mappings
    jac.project_mappings = []
    for proj_id in selected_project_ids:
        if proj_id:
            jac.project_mappings.append(JACProjectMapping(
                source_id=proj_id,
                source_name=jac.source_projects.get(proj_id, f"Project {proj_id}"),
                target_id=None,
                target_name="",
            ))
    
    # Create environment mappings
    jac.environment_mappings = []
    for env_id in selected_env_ids:
        if env_id:
            env_info = jac.source_environments.get(env_id, {})
            jac.environment_mappings.append(JACEnvironmentMapping(
                source_id=env_id,
                source_name=env_info.get("name", f"Environment {env_id}"),
                source_project_id=env_info.get("project_id", 0),
                target_id=None,
                target_name="",
            ))


def _create_mapping_summary(jac) -> None:
    """Create mapping completion summary."""
    projects_mapped = sum(1 for m in jac.project_mappings if m.target_id is not None)
    envs_mapped = sum(1 for m in jac.environment_mappings if m.target_id is not None)
    total_projects = len(jac.project_mappings)
    total_envs = len(jac.environment_mappings)
    
    all_complete = (projects_mapped == total_projects and envs_mapped == total_envs)
    
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Mapping Status").classes("text-lg font-semibold")
            
            if all_complete:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", size="md").classes("text-green-500")
                    ui.label("All mappings complete").classes("text-green-600 font-medium")
            else:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("pending", size="md").classes("text-amber-500")
                    ui.label("Mappings incomplete").classes("text-amber-600 font-medium")
        
        with ui.row().classes("gap-8 mt-4"):
            with ui.column().classes("items-center"):
                ui.label(f"{projects_mapped}/{total_projects}").classes("text-2xl font-bold")
                ui.label("Projects").classes("text-sm text-slate-500")
            
            with ui.column().classes("items-center"):
                ui.label(f"{envs_mapped}/{total_envs}").classes("text-2xl font-bold")
                ui.label("Environments").classes("text-sm text-slate-500")


def _create_project_mapping_table(jac, save_state: Callable[[], None]) -> None:
    """Create project mapping table."""
    # Build target options
    target_options = {"": "-- Select Target Project --"}
    target_options.update({
        str(k): f"{v} ({k})" for k, v in jac.target_projects.items()
    })
    
    with ui.column().classes("w-full gap-2"):
        # Header
        with ui.row().classes("w-full items-center py-2 border-b"):
            ui.label("Source Project").classes("w-1/3 font-semibold")
            ui.label("").classes("w-[40px]")
            ui.label("Target Project").classes("flex-grow font-semibold")
        
        # Rows
        for mapping in jac.project_mappings:
            with ui.row().classes("w-full items-center py-2"):
                with ui.column().classes("w-1/3"):
                    ui.label(mapping.source_name).classes("font-medium")
                    ui.label(f"ID: {mapping.source_id}").classes("text-xs text-slate-500")
                
                ui.icon("arrow_forward", size="sm").classes("text-slate-400")
                
                def make_handler(m):
                    def handler(e):
                        m.target_id = int(e.args) if e.args else None
                        m.target_name = jac.target_projects.get(m.target_id, "") if m.target_id else ""
                        save_state()
                    return handler
                
                ui.select(
                    options=target_options,
                    value=str(mapping.target_id) if mapping.target_id else "",
                    on_change=make_handler(mapping),
                ).classes("flex-grow").props("outlined dense")


def _create_environment_mapping_table(jac, save_state: Callable[[], None]) -> None:
    """Create environment mapping table."""
    # Build target options
    target_options = {"": "-- Select Target Environment --"}
    target_options.update({
        str(k): f"{v.get('name', f'Env {k}')} ({k})" 
        for k, v in jac.target_environments.items()
    })
    
    with ui.column().classes("w-full gap-2"):
        # Header
        with ui.row().classes("w-full items-center py-2 border-b"):
            ui.label("Source Environment").classes("w-1/3 font-semibold")
            ui.label("").classes("w-[40px]")
            ui.label("Target Environment").classes("flex-grow font-semibold")
        
        # Rows
        for mapping in jac.environment_mappings:
            with ui.row().classes("w-full items-center py-2"):
                with ui.column().classes("w-1/3"):
                    ui.label(mapping.source_name).classes("font-medium")
                    ui.label(f"ID: {mapping.source_id}").classes("text-xs text-slate-500")
                
                ui.icon("arrow_forward", size="sm").classes("text-slate-400")
                
                def make_handler(m):
                    def handler(e):
                        m.target_id = int(e.args) if e.args else None
                        env_info = jac.target_environments.get(m.target_id, {})
                        m.target_name = env_info.get("name", "") if m.target_id else ""
                        save_state()
                    return handler
                
                ui.select(
                    options=target_options,
                    value=str(mapping.target_id) if mapping.target_id else "",
                    on_change=make_handler(mapping),
                ).classes("flex-grow").props("outlined dense")


def _auto_match_by_name(
    mappings: list,
    source_lookup: dict,
    target_lookup: dict,
    is_project: bool = True,
) -> int:
    """Auto-match mappings by name.
    
    Args:
        mappings: List of JACProjectMapping or JACEnvironmentMapping
        source_lookup: Source ID to name mapping
        target_lookup: Target ID to name mapping
        is_project: True for projects, False for environments
        
    Returns:
        Number of matches found
    """
    # Build target name to ID lookup (lowercase)
    target_by_name = {}
    for target_id, target_name in target_lookup.items():
        if isinstance(target_name, dict):
            target_name = target_name.get("name", "")
        target_by_name[target_name.lower().strip()] = target_id
    
    matched = 0
    for mapping in mappings:
        source_name = mapping.source_name.lower().strip()
        if source_name in target_by_name:
            mapping.target_id = target_by_name[source_name]
            if is_project:
                mapping.target_name = target_lookup.get(mapping.target_id, "")
            else:
                env_info = target_lookup.get(mapping.target_id, {})
                if isinstance(env_info, dict):
                    mapping.target_name = env_info.get("name", "")
                else:
                    mapping.target_name = str(env_info)
            matched += 1
    
    if matched > 0:
        ui.notify(f"Auto-matched {matched} items by name", type="positive")
    else:
        ui.notify("No matches found by name", type="warning")
    
    return matched
