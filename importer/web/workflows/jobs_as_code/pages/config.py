"""Job configuration page for Jobs as Code Generator."""

from typing import Callable

from nicegui import ui

from importer.web.state import AppState, WorkflowStep, JACSubWorkflow, JACOutputFormat
from importer.web.workflows.jobs_as_code.utils.yaml_generator import sanitize_identifier


# dbt brand colors
DBT_ORANGE = "#FF694A"


def create_jac_config_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the job configuration page.
    
    Users configure job names, identifiers, trigger settings, and output format.
    
    Args:
        state: Application state
        on_step_change: Callback to navigate to a step
        save_state: Callback to save state
    """
    jac = state.jobs_as_code
    is_clone = jac.sub_workflow == JACSubWorkflow.CLONE
    
    # Get selected job configs
    selected_configs = [c for c in jac.job_configs if c.selected]
    
    with ui.column().classes("w-full max-w-5xl mx-auto p-8 gap-6"):
        # Header
        with ui.card().classes("w-full p-6"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.icon("tune", size="lg").style(f"color: {DBT_ORANGE};")
                ui.label("Configure Jobs").classes("text-2xl font-bold")
            
            workflow_label = (
                "Adopt Existing Jobs" if not is_clone else "Clone / Migrate Jobs"
            )
            ui.badge(workflow_label, color="orange").props("outline")
            
            ui.markdown(f"""
                Configure the {len(selected_configs)} selected jobs before generating YAML.
                {"Edit job names and identifiers as needed." if not is_clone else "Configure new names, trigger settings, and output format."}
            """).classes("text-slate-600 dark:text-slate-400 mt-3")
        
        # Bulk rename (clone workflow only)
        if is_clone:
            with ui.card().classes("w-full"):
                ui.label("Bulk Rename").classes("text-lg font-semibold mb-4")
                
                with ui.row().classes("w-full gap-4 items-end"):
                    prefix_input = ui.input(
                        label="Add Prefix",
                        value=jac.name_prefix,
                        placeholder="e.g., [QA] ",
                    ).classes("min-w-[200px]").props("outlined dense")
                    
                    suffix_input = ui.input(
                        label="Add Suffix",
                        value=jac.name_suffix,
                        placeholder="e.g., - QA",
                    ).classes("min-w-[200px]").props("outlined dense")
                    
                    def apply_bulk_rename():
                        prefix = prefix_input.value or ""
                        suffix = suffix_input.value or ""
                        
                        jac.name_prefix = prefix
                        jac.name_suffix = suffix
                        
                        for config in selected_configs:
                            new_name = f"{prefix}{config.original_name}{suffix}"
                            config.new_name = new_name
                            config.identifier = sanitize_identifier(new_name)
                        
                        save_state()
                        ui.notify(f"Applied prefix/suffix to {len(selected_configs)} jobs", type="positive")
                        ui.navigate.reload()
                    
                    ui.button(
                        "Apply to All",
                        icon="check",
                        on_click=apply_bulk_rename,
                    ).props("size=md")
        
        # Job table header
        ui.label("Job Configuration").classes("text-lg font-semibold")
        
        # Build row data
        rows = []
        jobs_by_id = {job.get("id"): job for job in jac.source_jobs}
        
        for config in selected_configs:
            job = jobs_by_id.get(config.job_id) or {}
            project = job.get("project") or {}
            
            # Get project name - fallback to ID if no project info
            project_id = job.get("project_id", "N/A")
            project_name = project.get("name") if project else None
            if not project_name:
                project_name = f"Project {project_id}"
            
            rows.append({
                "id": config.job_id,
                "original_name": config.original_name,
                "new_name": config.new_name,
                "identifier": config.identifier,
                "project_name": project_name,
                "is_managed": config.is_managed,
            })
        
        # Build columns
        columns = [
            {
                "field": "original_name",
                "headerName": "Original Name",
                "flex": 2,
            },
            {
                "field": "project_name",
                "headerName": "Project",
                "flex": 1,
            },
            {
                "field": "is_managed",
                "headerName": "Managed",
                "width": 100,
            },
        ]
        
        if is_clone:
            columns.insert(1, {
                "field": "new_name",
                "headerName": "New Name",
                "flex": 2,
                "editable": True,
            })
        
        columns.append({
            "field": "identifier",
            "headerName": "Identifier",
            "flex": 1,
            "editable": True,
            "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
        })
        
        # Convert rows to plain dicts for AG Grid compatibility
        plain_rows = [dict(r) for r in rows]
        
        grid = ui.aggrid({
            "columnDefs": columns,
            "rowData": plain_rows,
            "animateRows": False,
            "pagination": True,
            "paginationPageSize": 25,
            "paginationPageSizeSelector": [25, 50, 100],
            "headerHeight": 36,
            "defaultColDef": {
                "sortable": True,
                "resizable": True,
                "filter": True,
            },
        }, theme="balham").classes("w-full").style("height: 400px;")
        
        # Handle edits
        config_by_id = {c.job_id: c for c in jac.job_configs}
        
        async def handle_cell_edit(e):
            data = e.args.get("data", {})
            col = e.args.get("colId")
            job_id = data.get("id")
            
            config = config_by_id.get(job_id)
            if config:
                if col == "new_name":
                    config.new_name = data.get("new_name", "")
                elif col == "identifier":
                    config.identifier = data.get("identifier", "")
                save_state()
        
        grid.on("cellValueChanged", handle_cell_edit)
        
        # Trigger settings (clone workflow only)
        if is_clone:
            with ui.card().classes("w-full"):
                ui.label("Trigger Settings").classes("text-lg font-semibold mb-4")
                
                ui.markdown("""
                    By default, all triggers are disabled on cloned jobs to prevent unintended runs.
                    Enable them manually after verifying the jobs work correctly.
                """).classes("text-sm text-slate-500 mb-4")
                
                with ui.column().classes("gap-2"):
                    schedule_cb = ui.checkbox(
                        "Disable scheduled triggers",
                        value=jac.disable_schedule,
                    )
                    schedule_cb.on("update:model-value", lambda e: _update_trigger(jac, "schedule", e.args, save_state))
                    
                    github_cb = ui.checkbox(
                        "Disable GitHub webhook triggers",
                        value=jac.disable_github_webhook,
                    )
                    github_cb.on("update:model-value", lambda e: _update_trigger(jac, "github", e.args, save_state))
                    
                    git_cb = ui.checkbox(
                        "Disable Git provider webhook triggers",
                        value=jac.disable_git_provider_webhook,
                    )
                    git_cb.on("update:model-value", lambda e: _update_trigger(jac, "git", e.args, save_state))
                    
                    merge_cb = ui.checkbox(
                        "Disable on-merge triggers",
                        value=jac.disable_on_merge,
                    )
                    merge_cb.on("update:model-value", lambda e: _update_trigger(jac, "merge", e.args, save_state))
                
                with ui.row().classes("items-center gap-2 mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded"):
                    ui.icon("info", size="sm").classes("text-blue-500")
                    ui.label(
                        "Jobs will be created with triggers disabled. Enable them manually or update the YAML after verification."
                    ).classes("text-sm text-blue-700 dark:text-blue-300")
        
        # Output format (clone workflow only)
        if is_clone:
            with ui.card().classes("w-full"):
                ui.label("Output Format").classes("text-lg font-semibold mb-4")
                
                with ui.row().classes("gap-4"):
                    with ui.card().classes(
                        "flex-1 p-4 cursor-pointer " +
                        ("ring-2 ring-orange-400" if jac.output_format == JACOutputFormat.HARDCODED else "")
                    ).on("click", lambda: _set_output_format(jac, JACOutputFormat.HARDCODED, save_state)):
                        with ui.row().classes("items-center gap-2"):
                            ui.radio(
                                options={"hard": ""},
                                value="hard" if jac.output_format == JACOutputFormat.HARDCODED else None,
                            ).props("dense")
                            ui.label("Hardcoded IDs").classes("font-semibold")
                        
                        ui.markdown("""
                            YAML contains actual numeric IDs for account, project, and environment.
                            
                            - Simple and direct
                            - No additional files needed
                            - Good for one-time clones
                        """).classes("text-sm text-slate-500 mt-2")
                    
                    with ui.card().classes(
                        "flex-1 p-4 cursor-pointer " +
                        ("ring-2 ring-orange-400" if jac.output_format == JACOutputFormat.TEMPLATED else "")
                    ).on("click", lambda: _set_output_format(jac, JACOutputFormat.TEMPLATED, save_state)):
                        with ui.row().classes("items-center gap-2"):
                            ui.radio(
                                options={"temp": ""},
                                value="temp" if jac.output_format == JACOutputFormat.TEMPLATED else None,
                            ).props("dense")
                            ui.label("Jinja Templated").classes("font-semibold")
                        
                        ui.markdown("""
                            YAML uses `{{ variable }}` syntax for IDs. Generates a separate vars file.
                            
                            - Reusable across environments
                            - Requires vars.yml file
                            - Good for multi-environment setups
                        """).classes("text-sm text-slate-500 mt-2")
                
                if jac.output_format == JACOutputFormat.TEMPLATED:
                    with ui.row().classes("w-full mt-4"):
                        prefix_input = ui.input(
                            label="Variable Prefix (optional)",
                            value=jac.variable_prefix,
                            placeholder="e.g., prod_",
                        ).classes("w-64").props("outlined dense")
                        
                        prefix_input.on(
                            "update:model-value",
                            lambda e: _update_prefix(jac, e.args, save_state)
                        )
                        
                        ui.label(
                            f"Variables will be named: {{{{ {jac.variable_prefix or ''}account_id }}}}"
                        ).classes("text-sm text-slate-500 self-center ml-4")
        
        # Navigation
        with ui.row().classes("w-full justify-between items-center mt-4"):
            if is_clone:
                back_step = WorkflowStep.JAC_MAPPING
            else:
                back_step = WorkflowStep.JAC_JOBS
            
            ui.button(
                "Back",
                icon="arrow_back",
                on_click=lambda: on_step_change(back_step),
            ).props("outline")
            
            ui.button(
                "Generate YAML",
                icon="arrow_forward",
                on_click=lambda: on_step_change(WorkflowStep.JAC_GENERATE),
            ).props("size=lg").style(f"background-color: {DBT_ORANGE};")


def _update_trigger(jac, trigger_type: str, value: bool, save_state: Callable[[], None]) -> None:
    """Update a trigger setting."""
    if trigger_type == "schedule":
        jac.disable_schedule = value
    elif trigger_type == "github":
        jac.disable_github_webhook = value
    elif trigger_type == "git":
        jac.disable_git_provider_webhook = value
    elif trigger_type == "merge":
        jac.disable_on_merge = value
    save_state()


def _set_output_format(jac, format: JACOutputFormat, save_state: Callable[[], None]) -> None:
    """Set the output format."""
    jac.output_format = format
    save_state()
    ui.navigate.reload()


def _update_prefix(jac, value: str, save_state: Callable[[], None]) -> None:
    """Update the variable prefix."""
    jac.variable_prefix = value or ""
    save_state()
