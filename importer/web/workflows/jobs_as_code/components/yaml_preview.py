"""YAML preview component for Jobs as Code Generator."""

import base64
from typing import Callable, Optional

from nicegui import ui


# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_NAVY = "#1A1F36"


def create_yaml_preview(
    yaml_content: str,
    title: str = "Generated YAML",
    filename: str = "jobs.yml",
    on_download: Optional[Callable[[], None]] = None,
    on_copy: Optional[Callable[[], None]] = None,
    max_height: str = "500px",
) -> ui.element:
    """Create a YAML preview panel with syntax highlighting.
    
    Args:
        yaml_content: YAML content to display
        title: Title for the preview panel
        filename: Default filename for download
        on_download: Optional callback for download button
        on_copy: Optional callback for copy button
        max_height: Maximum height of the preview area
        
    Returns:
        The container element
    """
    with ui.card().classes("w-full") as card:
        with ui.row().classes("w-full items-center justify-between mb-2"):
            ui.label(title).classes("text-lg font-semibold")
            
            with ui.row().classes("gap-2"):
                # Copy button
                async def copy_to_clipboard():
                    await ui.run_javascript(
                        f"navigator.clipboard.writeText({repr(yaml_content)})"
                    )
                    ui.notify("Copied to clipboard!", type="positive")
                    if on_copy:
                        on_copy()
                
                ui.button(
                    "Copy",
                    icon="content_copy",
                    on_click=copy_to_clipboard,
                ).props("outline size=sm")
                
                # Download button
                def download_yaml():
                    # Create download link
                    b64 = base64.b64encode(yaml_content.encode()).decode()
                    ui.download(
                        src=f"data:text/yaml;base64,{b64}",
                        filename=filename,
                    )
                    ui.notify(f"Downloading {filename}", type="positive")
                    if on_download:
                        on_download()
                
                ui.button(
                    "Download",
                    icon="download",
                    on_click=download_yaml,
                ).props("size=sm").style(f"background-color: {DBT_ORANGE};")
        
        # YAML content with syntax highlighting
        # Using a code element with pre-formatted text
        with ui.scroll_area().classes("w-full").style(f"max-height: {max_height}"):
            ui.code(yaml_content, language="yaml").classes("w-full")
    
    return card


def create_dual_yaml_preview(
    jobs_yaml: str,
    vars_yaml: Optional[str] = None,
    jobs_filename: str = "jobs.yml",
    vars_filename: str = "vars.yml",
    on_download_all: Optional[Callable[[], None]] = None,
) -> ui.element:
    """Create a tabbed preview for jobs.yml and vars.yml.
    
    Args:
        jobs_yaml: Jobs YAML content
        vars_yaml: Optional vars YAML content (for templated output)
        jobs_filename: Filename for jobs YAML
        vars_filename: Filename for vars YAML
        on_download_all: Callback for download all button
        
    Returns:
        The container element
    """
    with ui.card().classes("w-full") as card:
        with ui.row().classes("w-full items-center justify-between mb-4"):
            ui.label("Generated Files").classes("text-xl font-semibold")
            
            if vars_yaml:
                # Download all button
                def download_all():
                    import zipfile
                    from io import BytesIO
                    
                    # Create zip in memory
                    buffer = BytesIO()
                    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                        zf.writestr(jobs_filename, jobs_yaml)
                        zf.writestr(vars_filename, vars_yaml)
                    
                    buffer.seek(0)
                    b64 = base64.b64encode(buffer.read()).decode()
                    
                    ui.download(
                        src=f"data:application/zip;base64,{b64}",
                        filename="jobs_as_code.zip",
                    )
                    ui.notify("Downloading jobs_as_code.zip", type="positive")
                    if on_download_all:
                        on_download_all()
                
                ui.button(
                    "Download All (.zip)",
                    icon="folder_zip",
                    on_click=download_all,
                ).props("size=sm").style(f"background-color: {DBT_ORANGE};")
        
        # Tabs for different files
        with ui.tabs().classes("w-full") as tabs:
            jobs_tab = ui.tab("jobs.yml", icon="code")
            if vars_yaml:
                vars_tab = ui.tab("vars.yml", icon="settings")
        
        with ui.tab_panels(tabs, value=jobs_tab).classes("w-full"):
            with ui.tab_panel(jobs_tab):
                create_yaml_preview(
                    jobs_yaml,
                    title="",
                    filename=jobs_filename,
                    max_height="400px",
                )
            
            if vars_yaml:
                with ui.tab_panel(vars_tab):
                    create_yaml_preview(
                        vars_yaml,
                        title="",
                        filename=vars_filename,
                        max_height="400px",
                    )
    
    return card


def create_validation_results(
    errors: list,
    warnings: Optional[list] = None,
) -> ui.element:
    """Create a validation results panel.
    
    Args:
        errors: List of validation errors
        warnings: Optional list of warnings
        
    Returns:
        The container element
    """
    warnings = warnings or []
    
    with ui.card().classes("w-full") as card:
        if not errors and not warnings:
            with ui.row().classes("items-center gap-2 text-green-600"):
                ui.icon("check_circle", size="md")
                ui.label("Validation passed").classes("text-lg font-semibold")
            return card
        
        if errors:
            with ui.expansion("Errors", icon="error").classes("w-full text-red-600"):
                for error in errors:
                    with ui.row().classes("items-start gap-2 py-1"):
                        ui.icon("error_outline", size="sm").classes("text-red-500 mt-1")
                        ui.label(str(error)).classes("text-sm")
        
        if warnings:
            with ui.expansion("Warnings", icon="warning").classes("w-full text-amber-600"):
                for warning in warnings:
                    with ui.row().classes("items-start gap-2 py-1"):
                        ui.icon("warning", size="sm").classes("text-amber-500 mt-1")
                        ui.label(str(warning)).classes("text-sm")
    
    return card


def create_next_steps_panel(
    is_adopt: bool = True,
    jobs_filename: str = "jobs.yml",
    vars_filename: str = "vars.yml",
) -> ui.element:
    """Create a panel showing next steps after generation.
    
    Args:
        is_adopt: True for adopt workflow, False for clone
        jobs_filename: Name of the jobs file
        vars_filename: Name of the vars file
        
    Returns:
        The container element
    """
    with ui.card().classes("w-full bg-blue-50 dark:bg-blue-900/20") as card:
        ui.label("Next Steps").classes("text-lg font-semibold mb-3")
        
        with ui.column().classes("gap-3"):
            # Step 1: Save files
            with ui.row().classes("items-start gap-2"):
                ui.badge("1").props("color=primary")
                ui.label("Save the generated YAML file(s) to your project")
            
            if is_adopt:
                # Adopt workflow steps
                with ui.row().classes("items-start gap-2"):
                    ui.badge("2").props("color=primary")
                    with ui.column().classes("gap-1"):
                        ui.label("Run the link command to adopt jobs:")
                        ui.code(
                            f"dbt-jobs-as-code link {jobs_filename}",
                            language="bash"
                        ).classes("text-sm")
                
                with ui.row().classes("items-start gap-2"):
                    ui.badge("3").props("color=primary")
                    ui.label("Verify jobs are linked with [[identifier]] in their names")
            else:
                # Clone workflow steps
                with ui.row().classes("items-start gap-2"):
                    ui.badge("2").props("color=primary")
                    with ui.column().classes("gap-1"):
                        ui.label("Review the plan:")
                        ui.code(
                            f"dbt-jobs-as-code plan {jobs_filename} --vars-yml {vars_filename}",
                            language="bash"
                        ).classes("text-sm")
                
                with ui.row().classes("items-start gap-2"):
                    ui.badge("3").props("color=primary")
                    with ui.column().classes("gap-1"):
                        ui.label("Apply changes to create jobs:")
                        ui.code(
                            f"dbt-jobs-as-code sync {jobs_filename} --vars-yml {vars_filename}",
                            language="bash"
                        ).classes("text-sm")
                
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
    
    return card
