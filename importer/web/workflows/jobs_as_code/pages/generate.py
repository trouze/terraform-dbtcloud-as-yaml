"""Generate and export page for Jobs as Code Generator."""

import base64
import zipfile
from io import BytesIO
from typing import Callable

from nicegui import ui

from importer.web.state import AppState, WorkflowStep, JACSubWorkflow, JACOutputFormat
from importer.web.workflows.jobs_as_code.utils.yaml_generator import (
    generate_jobs_yaml,
    generate_vars_yaml,
)
from importer.web.workflows.jobs_as_code.utils.validator import (
    validate_identifiers,
    validate_jobs_yaml,
    validate_yaml_full,
    is_dbt_jobs_as_code_available,
    JACValidationResult,
)


# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_NAVY = "#1A1F36"


def create_jac_generate_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the generate and export page.
    
    Users preview generated YAML and download files.
    
    Args:
        state: Application state
        on_step_change: Callback to navigate to a step
        save_state: Callback to save state
    """
    jac = state.jobs_as_code
    is_clone = jac.sub_workflow == JACSubWorkflow.CLONE
    is_templated = jac.output_format == JACOutputFormat.TEMPLATED and is_clone
    
    # Generate YAML if not already done
    if not jac.generated_yaml:
        _generate_yaml(state)
    
    # Validate
    validation_errors = validate_identifiers([c for c in jac.job_configs if c.selected])
    yaml_errors = validate_jobs_yaml(jac.generated_yaml) if jac.generated_yaml else []
    all_errors = validation_errors + yaml_errors
    
    # Get identifier warnings (auto-renamed duplicates - non-blocking)
    identifier_warnings = jac.identifier_warnings or []
    
    with ui.column().classes("w-full max-w-6xl mx-auto p-8 gap-6"):
        # Header
        with ui.card().classes("w-full p-6"):
            with ui.row().classes("items-center gap-3 mb-2"):
                ui.icon("code", size="lg").style(f"color: {DBT_ORANGE};")
                ui.label("Generated YAML").classes("text-2xl font-bold")
            
            workflow_label = (
                "Adopt Existing Jobs" if not is_clone else "Clone / Migrate Jobs"
            )
            ui.badge(workflow_label, color="orange").props("outline")
            
            selected_count = len([c for c in jac.job_configs if c.selected])
            ui.markdown(f"""
                Your **{selected_count} jobs** have been converted to dbt-jobs-as-code YAML format.
                Review the output below and download when ready.
            """).classes("text-slate-600 dark:text-slate-400 mt-3")
        
        # Validation warnings (non-blocking)
        if identifier_warnings:
            with ui.card().classes("w-full border-l-4 border-amber-500"):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("warning", size="md").classes("text-amber-500")
                    ui.label(f"{len(identifier_warnings)} identifiers auto-renamed").classes(
                        "text-lg font-semibold text-amber-600"
                    )
                
                ui.markdown("""
                    Some jobs had duplicate identifiers. They have been automatically 
                    renamed with numeric suffixes. You can edit them in the previous step if needed.
                """).classes("text-sm text-slate-500 mb-2")
                
                with ui.expansion("View Auto-renamed Identifiers").classes("w-full"):
                    for warning in identifier_warnings:
                        with ui.row().classes("items-start gap-2 py-1"):
                            ui.icon("edit", size="sm").classes("text-amber-500 mt-1")
                            ui.label(str(warning)).classes("text-sm")
        
        # Validation errors (blocking)
        if all_errors:
            with ui.card().classes("w-full border-l-4 border-red-500"):
                with ui.row().classes("items-center gap-2 mb-2"):
                    ui.icon("error", size="md").classes("text-red-500")
                    ui.label(f"{len(all_errors)} validation errors").classes(
                        "text-lg font-semibold text-red-600"
                    )
                
                with ui.expansion("View Errors").classes("w-full"):
                    for error in all_errors:
                        with ui.row().classes("items-start gap-2 py-1"):
                            ui.icon("error_outline", size="sm").classes("text-red-500 mt-1")
                            ui.label(str(error)).classes("text-sm")
        elif not identifier_warnings:
            # Only show "passed" if no warnings and no errors
            with ui.card().classes("w-full border-l-4 border-green-500"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", size="md").classes("text-green-500")
                    ui.label("Validation passed").classes(
                        "text-lg font-semibold text-green-600"
                    )
        elif not all_errors:
            # Warnings only, no errors - show success with note
            with ui.card().classes("w-full border-l-4 border-green-500"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check_circle", size="md").classes("text-green-500")
                    ui.label("Validation passed (with auto-fixes)").classes(
                        "text-lg font-semibold text-green-600"
                    )
        
        # dbt-jobs-as-code validation section
        _create_jac_validation_section(jac.generated_yaml)
        
        # YAML preview with tabs
        with ui.card().classes("w-full"):
            with ui.row().classes("w-full items-center justify-between mb-4"):
                ui.label("Preview").classes("text-xl font-semibold")
                
                with ui.row().classes("gap-2"):
                    # Regenerate button
                    def regenerate():
                        _generate_yaml(state)
                        save_state()
                        ui.navigate.reload()
                    
                    ui.button(
                        "Regenerate",
                        icon="refresh",
                        on_click=regenerate,
                    ).props("outline size=sm")
                    
                    # Download buttons
                    if is_templated:
                        ui.button(
                            "Download All (.zip)",
                            icon="folder_zip",
                            on_click=lambda: _download_zip(jac),
                        ).props("size=sm").style(f"background-color: {DBT_ORANGE};")
                    else:
                        ui.button(
                            "Download jobs.yml",
                            icon="download",
                            on_click=lambda: _download_yaml(jac.generated_yaml, "jobs.yml"),
                        ).props("size=sm").style(f"background-color: {DBT_ORANGE};")
            
            # Tabs for different files
            with ui.tabs().classes("w-full") as tabs:
                jobs_tab = ui.tab("jobs.yml", icon="code")
                if is_templated and jac.generated_vars_yaml:
                    vars_tab = ui.tab("vars.yml", icon="settings")
            
            with ui.tab_panels(tabs, value=jobs_tab).classes("w-full"):
                with ui.tab_panel(jobs_tab):
                    _create_yaml_preview(jac.generated_yaml, "jobs.yml")
                
                if is_templated and jac.generated_vars_yaml:
                    with ui.tab_panel(vars_tab):
                        _create_yaml_preview(jac.generated_vars_yaml, "vars.yml")
        
        # Next steps
        with ui.card().classes("w-full bg-blue-50 dark:bg-blue-900/20"):
            ui.label("Next Steps").classes("text-lg font-semibold mb-3")
            
            with ui.column().classes("gap-3"):
                with ui.row().classes("items-start gap-2"):
                    ui.badge("1").props("color=primary")
                    ui.label("Save the generated YAML file(s) to your project")
                
                if not is_clone:
                    # Adopt workflow steps
                    with ui.row().classes("items-start gap-2"):
                        ui.badge("2").props("color=primary")
                        with ui.column().classes("gap-1"):
                            ui.label("Run the link command to adopt jobs:")
                            ui.code(
                                "dbt-jobs-as-code link jobs.yml",
                                language="bash"
                            ).classes("text-sm")
                    
                    with ui.row().classes("items-start gap-2"):
                        ui.badge("3").props("color=primary")
                        ui.label("Verify jobs are linked with [[identifier]] in their names")
                else:
                    # Clone workflow steps
                    if is_templated:
                        cmd = "dbt-jobs-as-code plan jobs.yml --vars-yml vars.yml"
                        sync_cmd = "dbt-jobs-as-code sync jobs.yml --vars-yml vars.yml"
                    else:
                        cmd = "dbt-jobs-as-code plan jobs.yml"
                        sync_cmd = "dbt-jobs-as-code sync jobs.yml"
                    
                    with ui.row().classes("items-start gap-2"):
                        ui.badge("2").props("color=primary")
                        with ui.column().classes("gap-1"):
                            ui.label("Review the plan:")
                            ui.code(cmd, language="bash").classes("text-sm")
                    
                    with ui.row().classes("items-start gap-2"):
                        ui.badge("3").props("color=primary")
                        with ui.column().classes("gap-1"):
                            ui.label("Apply changes to create jobs:")
                            ui.code(sync_cmd, language="bash").classes("text-sm")
                    
                    with ui.row().classes("items-start gap-2"):
                        ui.badge("4").props("color=primary")
                        ui.label("Enable triggers after verifying jobs work correctly")
            
            # Documentation link
            with ui.row().classes("mt-4 items-center gap-2"):
                ui.icon("menu_book", size="sm").classes("text-blue-500")
                ui.link(
                    "dbt-jobs-as-code Documentation",
                    "https://github.com/dbt-labs/dbt-jobs-as-code",
                    new_tab=True,
                ).classes("text-sm text-blue-600 hover:underline")
        
        # Navigation
        with ui.row().classes("w-full justify-between items-center mt-4"):
            ui.button(
                "Back",
                icon="arrow_back",
                on_click=lambda: on_step_change(WorkflowStep.JAC_CONFIG),
            ).props("outline")
            
            def start_over():
                # Reset JAC state
                jac.source_jobs = []
                jac.job_configs = []
                jac.selected_job_ids = set()
                jac.fetch_complete = False
                jac.target_fetch_complete = False
                jac.project_mappings = []
                jac.environment_mappings = []
                jac.generated_yaml = ""
                jac.generated_vars_yaml = ""
                jac.generation_complete = False
                save_state()
                on_step_change(WorkflowStep.JAC_SELECT)
            
            ui.button(
                "Start New Generation",
                icon="restart_alt",
                on_click=start_over,
            ).props("outline")


def _generate_yaml(state: AppState) -> None:
    """Generate YAML from current state."""
    jac = state.jobs_as_code
    is_clone = jac.sub_workflow == JACSubWorkflow.CLONE
    
    # Build project/environment mappings for clone workflow
    project_mapping = {}
    environment_mapping = {}
    
    if is_clone:
        for m in jac.project_mappings:
            if m.target_id:
                project_mapping[m.source_id] = m.target_id
        
        for m in jac.environment_mappings:
            if m.target_id:
                environment_mapping[m.source_id] = m.target_id
    
    # Generate jobs YAML
    jac.generated_yaml = generate_jobs_yaml(
        jobs=jac.source_jobs,
        job_configs=[c for c in jac.job_configs if c.selected],
        sub_workflow=jac.sub_workflow,
        output_format=jac.output_format if is_clone else JACOutputFormat.HARDCODED,
        variable_prefix=jac.variable_prefix if is_clone else "",
        project_mapping=project_mapping,
        environment_mapping=environment_mapping,
        disable_schedule=jac.disable_schedule if is_clone else False,
        disable_github_webhook=jac.disable_github_webhook if is_clone else False,
        disable_git_provider_webhook=jac.disable_git_provider_webhook if is_clone else False,
        disable_on_merge=jac.disable_on_merge if is_clone else False,
    )
    
    # Generate vars YAML for templated output
    if is_clone and jac.output_format == JACOutputFormat.TEMPLATED:
        # Get target account ID
        if jac.target_same_account:
            account_id = int(state.source_credentials.account_id or 0)
        else:
            account_id = int(state.target_credentials.account_id or 0)
        
        jac.generated_vars_yaml = generate_vars_yaml(
            account_id=account_id,
            project_mapping=project_mapping,
            environment_mapping=environment_mapping,
            variable_prefix=jac.variable_prefix,
        )
    else:
        jac.generated_vars_yaml = ""
    
    jac.generation_complete = True


def _create_yaml_preview(yaml_content: str, filename: str) -> None:
    """Create YAML preview with copy and download buttons."""
    with ui.row().classes("w-full justify-end gap-2 mb-2"):
        async def copy_to_clipboard():
            await ui.run_javascript(
                f"navigator.clipboard.writeText({repr(yaml_content)})"
            )
            ui.notify("Copied to clipboard!", type="positive")
        
        ui.button(
            "Copy",
            icon="content_copy",
            on_click=copy_to_clipboard,
        ).props("outline size=sm")
        
        ui.button(
            "Download",
            icon="download",
            on_click=lambda: _download_yaml(yaml_content, filename),
        ).props("outline size=sm")
    
    with ui.scroll_area().classes("w-full").style("max-height: 400px;"):
        ui.code(yaml_content, language="yaml").classes("w-full")


def _download_yaml(content: str, filename: str) -> None:
    """Trigger download of YAML content."""
    b64 = base64.b64encode(content.encode()).decode()
    ui.download(
        src=f"data:text/yaml;base64,{b64}",
        filename=filename,
    )
    ui.notify(f"Downloading {filename}", type="positive")


def _download_zip(jac) -> None:
    """Download all files as a zip archive."""
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("jobs.yml", jac.generated_yaml)
        if jac.generated_vars_yaml:
            zf.writestr("vars.yml", jac.generated_vars_yaml)
    
    buffer.seek(0)
    b64 = base64.b64encode(buffer.read()).decode()
    
    ui.download(
        src=f"data:application/zip;base64,{b64}",
        filename="jobs_as_code.zip",
    )
    ui.notify("Downloading jobs_as_code.zip", type="positive")


def _create_jac_validation_section(yaml_content: str) -> None:
    """Create the dbt-jobs-as-code validation section.
    
    Args:
        yaml_content: The YAML content to validate
    """
    jac_available = is_dbt_jobs_as_code_available()
    
    with ui.card().classes("w-full"):
        with ui.row().classes("w-full items-center justify-between mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("verified", size="md").style(f"color: {DBT_ORANGE};")
                ui.label("dbt-jobs-as-code Validation").classes("text-lg font-semibold")
            
            if jac_available:
                ui.badge("Available", color="green").props("outline")
            else:
                ui.badge("Not Installed", color="grey").props("outline")
        
        if not jac_available:
            # Show installation instructions
            ui.markdown("""
                **Optional:** Install `dbt-jobs-as-code` for enhanced validation using the official schema.
                
                This validates your YAML against the same schema used by the `dbt-jobs-as-code` CLI tool.
            """).classes("text-sm text-slate-500 mb-3")
            
            with ui.card().classes("w-full bg-slate-100 dark:bg-slate-800 p-3"):
                ui.label("Installation").classes("text-sm font-semibold mb-2")
                ui.code("pip install dbt-jobs-as-code", language="bash").classes("text-sm")
                
                ui.label("Then restart the web server.").classes("text-xs text-slate-400 mt-2")
        else:
            # Show validation UI
            ui.markdown("""
                Validate your YAML against the official dbt-jobs-as-code schema.
                This ensures compatibility with the `dbt-jobs-as-code` CLI tool.
            """).classes("text-sm text-slate-500 mb-3")
            
            # Container for validation results
            results_container = ui.column().classes("w-full")
            
            async def run_validation():
                """Run validation and display results."""
                results_container.clear()
                
                with results_container:
                    with ui.row().classes("items-center gap-2 mb-2"):
                        spinner = ui.spinner(size="sm")
                        ui.label("Validating...").classes("text-sm text-slate-500")
                
                # Run validation (this is sync but we await for UI update)
                result = validate_yaml_full(yaml_content, prefer_jac=True)
                
                results_container.clear()
                with results_container:
                    _display_validation_result(result)
            
            ui.button(
                "Validate with dbt-jobs-as-code",
                icon="play_arrow",
                on_click=run_validation,
            ).props("size=sm").style(f"background-color: {DBT_ORANGE};")


def _display_validation_result(result: JACValidationResult) -> None:
    """Display validation results in the UI.
    
    Args:
        result: The validation result to display
    """
    if result.is_valid:
        with ui.card().classes("w-full border-l-4 border-green-500 mt-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("check_circle", size="md").classes("text-green-500")
                ui.label(result.summary).classes("text-green-600 font-semibold")
            
            if result.warnings:
                with ui.expansion(f"View {len(result.warnings)} warnings").classes("w-full mt-2"):
                    for warning in result.warnings:
                        with ui.row().classes("items-start gap-2 py-1"):
                            ui.icon("warning", size="sm").classes("text-amber-500 mt-1")
                            ui.label(warning).classes("text-sm")
    else:
        with ui.card().classes("w-full border-l-4 border-red-500 mt-3"):
            with ui.row().classes("items-center gap-2 mb-2"):
                ui.icon("error", size="md").classes("text-red-500")
                ui.label(result.summary).classes("text-red-600 font-semibold")
            
            with ui.expansion(f"View {len(result.errors)} errors").classes("w-full"):
                for error in result.errors:
                    with ui.row().classes("items-start gap-2 py-1"):
                        ui.icon("error_outline", size="sm").classes("text-red-500 mt-1")
                        ui.label(error).classes("text-sm")
            
            if result.warnings:
                with ui.expansion(f"View {len(result.warnings)} warnings").classes("w-full mt-2"):
                    for warning in result.warnings:
                        with ui.row().classes("items-start gap-2 py-1"):
                            ui.icon("warning", size="sm").classes("text-amber-500 mt-1")
                            ui.label(warning).classes("text-sm")
