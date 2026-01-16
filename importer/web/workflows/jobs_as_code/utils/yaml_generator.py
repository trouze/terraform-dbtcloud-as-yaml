"""YAML generation utilities for Jobs as Code Generator."""

import re
from typing import Any, Optional

import yaml

from importer.web.state import JACSubWorkflow, JACOutputFormat, JACJobConfig


def _to_plain_python(obj: Any) -> Any:
    """Recursively convert NiceGUI observable objects to plain Python.
    
    NiceGUI uses ObservableDict and ObservableList for state management,
    but PyYAML doesn't serialize these properly. This converts them to
    standard Python dict and list types.
    
    Args:
        obj: Any object that might be an observable
        
    Returns:
        Plain Python equivalent (dict, list, or original value)
    """
    # Handle dict-like objects (including ObservableDict)
    if hasattr(obj, 'items') and callable(getattr(obj, 'items')):
        return {k: _to_plain_python(v) for k, v in obj.items()}
    
    # Handle list-like objects (including ObservableList)
    if hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes)):
        try:
            return [_to_plain_python(item) for item in obj]
        except TypeError:
            return obj
    
    return obj


# Schema URL for dbt-jobs-as-code
SCHEMA_URL = "https://raw.githubusercontent.com/dbt-labs/dbt-jobs-as-code/main/src/dbt_jobs_as_code/schemas/load_job_schema.json"


def sanitize_identifier(name: str) -> str:
    """Convert a job name to a valid YAML identifier.
    
    Args:
        name: Job name to sanitize
        
    Returns:
        Sanitized identifier (lowercase, underscores for spaces, alphanumeric only)
    """
    # Remove any existing [[identifier]] pattern
    name = re.sub(r"\s*\[\[[^\]]+\]\]\s*", "", name)
    
    # Convert to lowercase
    identifier = name.lower()
    
    # Replace spaces and hyphens with underscores
    identifier = re.sub(r"[\s\-]+", "_", identifier)
    
    # Remove non-alphanumeric characters (except underscores)
    identifier = re.sub(r"[^a-z0-9_]", "", identifier)
    
    # Remove consecutive underscores
    identifier = re.sub(r"_+", "_", identifier)
    
    # Remove leading/trailing underscores
    identifier = identifier.strip("_")
    
    # Ensure it doesn't start with a number
    if identifier and identifier[0].isdigit():
        identifier = f"job_{identifier}"
    
    return identifier or "unnamed_job"


def _is_ci_or_merge_job(job: dict) -> bool:
    """Check if job is CI or Merge type (SAO force_node_selection not applicable).
    
    Args:
        job: Job dictionary from API
        
    Returns:
        True if job is CI or Merge type
    """
    triggers = job.get("triggers", {})
    return (
        triggers.get("github_webhook", False) or
        triggers.get("git_provider_webhook", False) or
        triggers.get("on_merge", False) or
        job.get("job_type") in ("ci", "merge")
    )


def _build_triggers_dict(
    job: dict,
    disable_schedule: bool = False,
    disable_github_webhook: bool = False,
    disable_git_provider_webhook: bool = False,
    disable_on_merge: bool = False,
) -> dict:
    """Build triggers dictionary for a job.
    
    Args:
        job: Original job dictionary
        disable_*: Flags to disable specific trigger types
        
    Returns:
        Triggers configuration dictionary
    """
    triggers = job.get("triggers", {})
    
    return {
        "github_webhook": False if disable_github_webhook else triggers.get("github_webhook", False),
        "git_provider_webhook": False if disable_git_provider_webhook else triggers.get("git_provider_webhook", False),
        "schedule": False if disable_schedule else triggers.get("schedule", False),
        "on_merge": False if disable_on_merge else triggers.get("on_merge", False),
    }


def _build_schedule_dict(job: dict) -> dict:
    """Build schedule dictionary for a job.
    
    Args:
        job: Original job dictionary
        
    Returns:
        Schedule configuration dictionary
    """
    schedule = job.get("schedule", {})
    
    return {
        "cron": schedule.get("cron", "0 0 * * *"),
    }


def _build_settings_dict(job: dict) -> dict:
    """Build settings dictionary for a job.
    
    Args:
        job: Original job dictionary
        
    Returns:
        Settings configuration dictionary
    """
    settings = job.get("settings", {})
    
    return {
        "threads": settings.get("threads", 4),
        "target_name": settings.get("target_name", "default"),
    }


def _build_execution_dict(job: dict) -> dict:
    """Build execution dictionary for a job.
    
    Args:
        job: Original job dictionary
        
    Returns:
        Execution configuration dictionary
    """
    execution = job.get("execution", {})
    
    return {
        "timeout_seconds": execution.get("timeout_seconds", 0),
    }


def _build_job_dict(
    job: dict,
    config: JACJobConfig,
    sub_workflow: JACSubWorkflow,
    output_format: JACOutputFormat,
    variable_prefix: str = "",
    project_mapping: Optional[dict[int, int]] = None,
    environment_mapping: Optional[dict[int, int]] = None,
    disable_triggers: bool = False,
    disable_schedule: bool = True,
    disable_github_webhook: bool = True,
    disable_git_provider_webhook: bool = True,
    disable_on_merge: bool = True,
) -> dict:
    """Build a job dictionary for YAML output.
    
    Args:
        job: Original job dictionary from API
        config: Job configuration
        sub_workflow: Adopt or Clone workflow
        output_format: Templated or Hardcoded
        variable_prefix: Prefix for template variables
        project_mapping: Source to target project ID mapping
        environment_mapping: Source to target environment ID mapping
        disable_triggers: Whether to disable all triggers
        disable_*: Individual trigger disable flags
        
    Returns:
        Job dictionary ready for YAML serialization
    """
    # Convert job to plain Python first to handle NiceGUI observables
    job = _to_plain_python(job)
    
    project_mapping = project_mapping or {}
    environment_mapping = environment_mapping or {}
    
    # Determine IDs based on workflow
    if sub_workflow == JACSubWorkflow.ADOPT:
        # Adopt: Keep original IDs, add linked_id
        account_id = job.get("account_id")
        project_id = job.get("project_id")
        environment_id = job.get("environment_id")
    else:
        # Clone: Map to target IDs
        source_project_id = job.get("project_id")
        source_env_id = job.get("environment_id")
        
        if output_format == JACOutputFormat.TEMPLATED:
            # Use Jinja variables
            prefix = variable_prefix or ""
            account_id = f"{{{{ {prefix}account_id }}}}"
            project_id = f"{{{{ {prefix}project_id }}}}"
            environment_id = f"{{{{ {prefix}environment_id }}}}"
        else:
            # Use mapped hardcoded IDs
            account_id = job.get("account_id")  # Usually same account
            project_id = project_mapping.get(source_project_id, source_project_id)
            environment_id = environment_mapping.get(source_env_id, source_env_id)
    
    # Build the job dictionary
    job_dict = {
        "account_id": account_id,
        "project_id": project_id,
        "environment_id": environment_id,
        "name": config.new_name or job.get("name", ""),
        "settings": _build_settings_dict(job),
        "execution": _build_execution_dict(job),
        "run_generate_sources": job.get("run_generate_sources", False),
        "execute_steps": list(job.get("execute_steps", ["dbt build"])),  # Ensure plain list
        "generate_docs": job.get("generate_docs", False),
        "schedule": _build_schedule_dict(job),
        "triggers": _build_triggers_dict(
            job,
            disable_schedule=disable_schedule if sub_workflow == JACSubWorkflow.CLONE else False,
            disable_github_webhook=disable_github_webhook if sub_workflow == JACSubWorkflow.CLONE else False,
            disable_git_provider_webhook=disable_git_provider_webhook if sub_workflow == JACSubWorkflow.CLONE else False,
            disable_on_merge=disable_on_merge if sub_workflow == JACSubWorkflow.CLONE else False,
        ),
    }
    
    # Add linked_id for adopt workflow
    if sub_workflow == JACSubWorkflow.ADOPT:
        job_dict["linked_id"] = job.get("id")
    
    # Add optional fields if present
    if job.get("description"):
        job_dict["description"] = job.get("description")
        
    if job.get("dbt_version"):
        job_dict["dbt_version"] = job.get("dbt_version")
        
    if job.get("deferring_job_definition_id"):
        job_dict["deferring_job_definition_id"] = job.get("deferring_job_definition_id")
        
    if job.get("deferring_environment_id"):
        job_dict["deferring_environment_id"] = job.get("deferring_environment_id")
        
    if job.get("job_type"):
        job_dict["job_type"] = job.get("job_type")
        
    if job.get("run_lint"):
        job_dict["run_lint"] = job.get("run_lint")
        
    if job.get("run_compare_changes"):
        job_dict["run_compare_changes"] = job.get("run_compare_changes")
        
    if job.get("triggers_on_draft_pr"):
        job_dict["triggers_on_draft_pr"] = job.get("triggers_on_draft_pr")
    
    # SAO (State-Aware Orchestration) fields
    # force_node_selection: Only include for non-CI/Merge jobs (API rejects for CI/Merge)
    if not _is_ci_or_merge_job(job):
        force_node_sel = job.get("force_node_selection")
        if force_node_sel is not None:
            job_dict["force_node_selection"] = force_node_sel
    
    # cost_optimization_features: Include if present (applies to all job types)
    cost_opt = job.get("cost_optimization_features")
    if cost_opt:
        job_dict["cost_optimization_features"] = list(cost_opt)
    
    return job_dict


def generate_jobs_yaml(
    jobs: list[dict],
    job_configs: list[JACJobConfig],
    sub_workflow: JACSubWorkflow,
    output_format: JACOutputFormat = JACOutputFormat.HARDCODED,
    variable_prefix: str = "",
    project_mapping: Optional[dict[int, int]] = None,
    environment_mapping: Optional[dict[int, int]] = None,
    disable_schedule: bool = True,
    disable_github_webhook: bool = True,
    disable_git_provider_webhook: bool = True,
    disable_on_merge: bool = True,
) -> str:
    """Generate jobs-as-code YAML from job data.
    
    Args:
        jobs: List of job dictionaries from API
        job_configs: List of job configurations with identifiers and names
        sub_workflow: Adopt or Clone workflow
        output_format: Templated or Hardcoded
        variable_prefix: Prefix for template variables
        project_mapping: Source to target project ID mapping
        environment_mapping: Source to target environment ID mapping
        disable_*: Trigger disable flags for clone workflow
        
    Returns:
        Generated YAML string
    """
    # Create job lookup by ID
    jobs_by_id = {job.get("id"): job for job in jobs}
    
    # Build jobs dictionary
    jobs_dict = {}
    for config in job_configs:
        if not config.selected:
            continue
            
        job = jobs_by_id.get(config.job_id)
        if not job:
            continue
            
        job_dict = _build_job_dict(
            job=job,
            config=config,
            sub_workflow=sub_workflow,
            output_format=output_format,
            variable_prefix=variable_prefix,
            project_mapping=project_mapping,
            environment_mapping=environment_mapping,
            disable_schedule=disable_schedule,
            disable_github_webhook=disable_github_webhook,
            disable_git_provider_webhook=disable_git_provider_webhook,
            disable_on_merge=disable_on_merge,
        )
        
        jobs_dict[config.identifier] = job_dict
    
    # Build YAML output
    export_dict = {"jobs": jobs_dict}
    
    # Add schema comment
    output = f"# yaml-language-server: $schema={SCHEMA_URL}\n\n"
    
    # Dump YAML with proper formatting
    output += yaml.dump(export_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    return output


def generate_vars_yaml(
    account_id: int,
    project_mapping: dict[int, int],
    environment_mapping: dict[int, int],
    variable_prefix: str = "",
) -> str:
    """Generate vars YAML file for templated output.
    
    Args:
        account_id: Target account ID
        project_mapping: Source to target project ID mapping
        environment_mapping: Source to target environment ID mapping
        variable_prefix: Prefix for variable names
        
    Returns:
        Generated vars YAML string
    """
    prefix = variable_prefix or ""
    
    vars_dict = {
        f"{prefix}account_id": account_id,
    }
    
    # Add project mappings
    for idx, (source_id, target_id) in enumerate(project_mapping.items()):
        if idx == 0:
            vars_dict[f"{prefix}project_id"] = target_id
        else:
            vars_dict[f"{prefix}project_{idx}_id"] = target_id
    
    # Add environment mappings
    for idx, (source_id, target_id) in enumerate(environment_mapping.items()):
        if idx == 0:
            vars_dict[f"{prefix}environment_id"] = target_id
        else:
            vars_dict[f"{prefix}environment_{idx}_id"] = target_id
    
    # Build output
    output = "# Variables file for dbt-jobs-as-code\n"
    output += "# Use with: dbt-jobs-as-code plan jobs.yml --vars-yml vars.yml\n\n"
    
    output += yaml.dump(vars_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    return output
