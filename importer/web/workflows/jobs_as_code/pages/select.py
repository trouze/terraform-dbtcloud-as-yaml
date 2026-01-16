"""Workflow selection page for Jobs as Code Generator."""

from typing import Callable

from nicegui import ui

from importer.web.state import AppState, WorkflowStep, JACSubWorkflow


# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_NAVY = "#1A1F36"


def create_jac_select_page(
    state: AppState,
    on_step_change: Callable[[WorkflowStep], None],
    save_state: Callable[[], None],
) -> None:
    """Create the workflow selection page.
    
    Users choose between:
    - Adopt: Take existing jobs under jobs-as-code management
    - Clone: Create copies of jobs in different environments
    
    Args:
        state: Application state
        on_step_change: Callback to navigate to a step
        save_state: Callback to save state
    """
    @ui.refreshable
    def workflow_cards() -> None:
        """Refreshable container for workflow selection cards."""
        # Read current sub_workflow from state (inside refreshable to get latest value)
        current_workflow = state.jobs_as_code.sub_workflow
        
        with ui.row().classes("w-full gap-6"):
            # Adopt card
            _create_workflow_card(
                title="Adopt Existing Jobs",
                icon="download",
                description="""
                    Take your existing dbt Cloud jobs under **dbt-jobs-as-code** management.
                    
                    - Jobs keep their current IDs
                    - Generated YAML includes `linked_id` for each job
                    - Run `dbt-jobs-as-code link` to adopt
                    - Job names get `[[identifier]]` suffix
                """,
                benefits=[
                    "No changes to existing jobs",
                    "Gradual adoption possible",
                    "Version control your job configs",
                ],
                is_selected=current_workflow == JACSubWorkflow.ADOPT,
                on_select=lambda: _select_workflow(state, JACSubWorkflow.ADOPT, save_state, workflow_cards.refresh),
            )
            
            # Clone card
            _create_workflow_card(
                title="Clone / Migrate Jobs",
                icon="content_copy",
                description="""
                    Create copies of jobs in a different environment, project, or account.
                    
                    - Map source resources to target resources
                    - Triggers disabled by default (safety)
                    - Generate Jinja-templated or hardcoded YAML
                    - Run `dbt-jobs-as-code sync` to create jobs
                """,
                benefits=[
                    "Duplicate jobs across environments",
                    "Cross-account migration support",
                    "Bulk job creation",
                ],
                is_selected=current_workflow == JACSubWorkflow.CLONE,
                on_select=lambda: _select_workflow(state, JACSubWorkflow.CLONE, save_state, workflow_cards.refresh),
            )
    
    with ui.column().classes("w-full max-w-4xl mx-auto p-8 gap-8"):
        # Header
        with ui.card().classes("w-full p-6"):
            with ui.row().classes("items-center gap-3 mb-4"):
                ui.icon("code", size="lg").style(f"color: {DBT_ORANGE};")
                ui.label("Jobs as Code Generator").classes("text-2xl font-bold")
            
            ui.markdown("""
                Generate **dbt-jobs-as-code** compatible YAML files from your existing dbt Cloud jobs.
                Choose a workflow below based on your goal.
            """).classes("text-slate-600 dark:text-slate-400")
        
        # Workflow selection cards (refreshable)
        workflow_cards()
        
        # Continue button
        with ui.row().classes("w-full justify-end mt-4"):
            ui.button(
                "Continue",
                icon="arrow_forward",
                on_click=lambda: on_step_change(WorkflowStep.JAC_FETCH),
            ).props("size=lg").style(f"background-color: {DBT_ORANGE};")


def _create_workflow_card(
    title: str,
    icon: str,
    description: str,
    benefits: list[str],
    is_selected: bool,
    on_select: Callable[[], None],
) -> None:
    """Create a workflow selection card.
    
    Args:
        title: Card title
        icon: Material icon name
        description: Markdown description
        benefits: List of benefit bullet points
        is_selected: Whether this workflow is currently selected
        on_select: Callback when card is selected
    """
    card_classes = "flex-1 p-6 cursor-pointer transition-all"
    if is_selected:
        card_classes += " ring-2 ring-orange-400 bg-orange-50 dark:bg-orange-900/20"
    
    with ui.card().classes(card_classes).on("click", on_select):
        with ui.row().classes("items-center gap-3 mb-4"):
            ui.icon(icon, size="lg").style(
                f"color: {DBT_ORANGE if is_selected else '#64748b'};"
            )
            ui.label(title).classes("text-xl font-semibold")
            
            if is_selected:
                ui.icon("check_circle", size="sm").classes("text-orange-500 ml-auto")
        
        ui.markdown(description).classes("text-sm text-slate-600 dark:text-slate-400 mb-4")
        
        ui.label("Benefits:").classes("text-sm font-semibold text-slate-500 mb-2")
        
        with ui.column().classes("gap-1"):
            for benefit in benefits:
                with ui.row().classes("items-center gap-2"):
                    ui.icon("check", size="xs").classes("text-green-500")
                    ui.label(benefit).classes("text-sm text-slate-600")


def _select_workflow(
    state: AppState,
    workflow: JACSubWorkflow,
    save_state: Callable[[], None],
    refresh_ui: Callable[[], None],
) -> None:
    """Select a sub-workflow.
    
    Args:
        state: Application state
        workflow: The workflow to select
        save_state: Callback to save state
        refresh_ui: Callback to refresh the UI
    """
    state.jobs_as_code.sub_workflow = workflow
    save_state()
    refresh_ui()
    ui.notify(
        f"Selected: {'Adopt Existing Jobs' if workflow == JACSubWorkflow.ADOPT else 'Clone / Migrate Jobs'}",
        type="positive"
    )
