"""Validation utilities for Jobs as Code Generator."""

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from importer.web.state import JACJobConfig


# Check if dbt-jobs-as-code is available
_DBT_JOBS_AS_CODE_AVAILABLE = False
try:
    from dbt_jobs_as_code.loader.load import load_job_configuration, LoadingJobsYAMLError
    from pydantic import ValidationError as PydanticValidationError
    _DBT_JOBS_AS_CODE_AVAILABLE = True
except ImportError:
    pass


def is_dbt_jobs_as_code_available() -> bool:
    """Check if dbt-jobs-as-code is installed and available."""
    return _DBT_JOBS_AS_CODE_AVAILABLE


@dataclass
class JACValidationResult:
    """Result of dbt-jobs-as-code validation."""
    
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    job_count: int
    validated_with_jac: bool  # True if validated with dbt-jobs-as-code
    
    @property
    def summary(self) -> str:
        """Human-readable summary of validation results."""
        if self.is_valid:
            method = "dbt-jobs-as-code" if self.validated_with_jac else "basic schema"
            return f"✅ Valid ({self.job_count} jobs validated with {method})"
        return f"❌ Invalid ({len(self.errors)} errors)"


class ValidationWarning:
    """Represents a non-blocking validation warning."""
    
    def __init__(self, field: str, message: str, job_id: Optional[int] = None):
        self.field = field
        self.message = message
        self.job_id = job_id
        
    def __str__(self) -> str:
        if self.job_id:
            return f"[Job {self.job_id}] {self.field}: {self.message}"
        return f"{self.field}: {self.message}"


class ValidationError:
    """Represents a validation error."""
    
    def __init__(self, field: str, message: str, job_id: Optional[int] = None):
        self.field = field
        self.message = message
        self.job_id = job_id
        
    def __str__(self) -> str:
        if self.job_id:
            return f"[Job {self.job_id}] {self.field}: {self.message}"
        return f"{self.field}: {self.message}"


def deduplicate_identifiers(
    job_configs: list[JACJobConfig],
) -> tuple[list[JACJobConfig], list[ValidationWarning]]:
    """Automatically deduplicate identifiers by appending numeric suffixes.
    
    When multiple jobs would have the same identifier, this function appends
    _2, _3, etc. to make them unique. Returns warnings for each modified identifier.
    
    Args:
        job_configs: List of job configurations to deduplicate
        
    Returns:
        Tuple of (updated configs, list of warnings for modified identifiers)
    """
    warnings: list[ValidationWarning] = []
    seen_identifiers: dict[str, list[JACJobConfig]] = {}
    
    # Group configs by identifier
    for config in job_configs:
        identifier = config.identifier
        if identifier not in seen_identifiers:
            seen_identifiers[identifier] = []
        seen_identifiers[identifier].append(config)
    
    # Deduplicate - append suffixes for duplicates
    for identifier, configs in seen_identifiers.items():
        if len(configs) > 1:
            # First occurrence keeps the original identifier
            # Subsequent occurrences get _2, _3, etc.
            for i, config in enumerate(configs):
                if i == 0:
                    continue  # Keep original
                
                # Find next available suffix
                suffix_num = i + 1
                new_identifier = f"{identifier}_{suffix_num}"
                
                # Make sure the new identifier doesn't collide
                while new_identifier in seen_identifiers:
                    suffix_num += 1
                    new_identifier = f"{identifier}_{suffix_num}"
                
                old_identifier = config.identifier
                config.identifier = new_identifier
                
                warnings.append(ValidationWarning(
                    "identifier",
                    f"Renamed from '{old_identifier}' to '{new_identifier}' (duplicate with job {configs[0].job_id})",
                    config.job_id
                ))
    
    return job_configs, warnings


def validate_identifier(identifier: str) -> list[str]:
    """Validate a single job identifier.
    
    Args:
        identifier: The identifier to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not identifier:
        errors.append("Identifier cannot be empty")
        return errors
    
    # Check length
    if len(identifier) > 100:
        errors.append("Identifier must be 100 characters or less")
    
    # Check for valid characters
    if not re.match(r"^[a-z][a-z0-9_]*$", identifier):
        if identifier[0].isdigit():
            errors.append("Identifier cannot start with a number")
        elif identifier[0] == "_":
            errors.append("Identifier cannot start with underscore")
        elif not identifier[0].isalpha():
            errors.append("Identifier must start with a letter")
        
        invalid_chars = re.findall(r"[^a-z0-9_]", identifier)
        if invalid_chars:
            errors.append(f"Invalid characters: {', '.join(set(invalid_chars))}")
    
    # Check for reserved words
    reserved = {"jobs", "job", "import", "export", "config", "settings", "triggers"}
    if identifier.lower() in reserved:
        errors.append(f"'{identifier}' is a reserved word")
    
    return errors


def validate_identifiers(job_configs: list[JACJobConfig]) -> list[ValidationError]:
    """Validate all job identifiers for uniqueness and format.
    
    Args:
        job_configs: List of job configurations
        
    Returns:
        List of validation errors
    """
    errors = []
    seen_identifiers: dict[str, int] = {}  # identifier -> job_id
    
    for config in job_configs:
        if not config.selected:
            continue
            
        identifier = config.identifier
        
        # Check format
        format_errors = validate_identifier(identifier)
        for error in format_errors:
            errors.append(ValidationError("identifier", error, config.job_id))
        
        # Check uniqueness
        if identifier in seen_identifiers:
            errors.append(ValidationError(
                "identifier",
                f"Duplicate identifier '{identifier}' (also used by job {seen_identifiers[identifier]})",
                config.job_id
            ))
        else:
            seen_identifiers[identifier] = config.job_id
    
    return errors


def validate_job_name(name: str) -> list[str]:
    """Validate a job name.
    
    Args:
        name: The job name to validate
        
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not name:
        errors.append("Job name cannot be empty")
        return errors
    
    if len(name) > 255:
        errors.append("Job name must be 255 characters or less")
    
    # Check for problematic characters
    if "[[" in name or "]]" in name:
        errors.append("Job name should not contain [[ or ]] (reserved for identifiers)")
    
    return errors


def validate_jobs_yaml(yaml_content: str) -> list[ValidationError]:
    """Validate generated YAML content.
    
    Args:
        yaml_content: The YAML content to validate
        
    Returns:
        List of validation errors
    """
    errors = []
    
    if not yaml_content:
        errors.append(ValidationError("yaml", "YAML content is empty"))
        return errors
    
    try:
        import yaml as pyyaml
        data = pyyaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            errors.append(ValidationError("yaml", "Root must be a dictionary"))
            return errors
            
        if "jobs" not in data:
            errors.append(ValidationError("yaml", "Missing 'jobs' key"))
            return errors
            
        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            errors.append(ValidationError("jobs", "Jobs must be a dictionary"))
            return errors
            
        for identifier, job in jobs.items():
            # Validate each job has required fields
            required_fields = ["account_id", "project_id", "environment_id", "name"]
            for field in required_fields:
                if field not in job:
                    errors.append(ValidationError(
                        field,
                        f"Missing required field '{field}'",
                        job.get("linked_id")
                    ))
                    
    except Exception as e:
        errors.append(ValidationError("yaml", f"Invalid YAML: {str(e)}"))
    
    return errors


def validate_mappings(
    job_configs: list[JACJobConfig],
    jobs: list[dict],
    project_mapping: dict[int, int],
    environment_mapping: dict[int, int],
) -> list[ValidationError]:
    """Validate project and environment mappings for clone workflow.
    
    Args:
        job_configs: List of job configurations
        jobs: List of source job dictionaries
        project_mapping: Source to target project mapping
        environment_mapping: Source to target environment mapping
        
    Returns:
        List of validation errors
    """
    errors = []
    
    jobs_by_id = {job.get("id"): job for job in jobs}
    
    for config in job_configs:
        if not config.selected:
            continue
            
        job = jobs_by_id.get(config.job_id)
        if not job:
            continue
            
        project_id = job.get("project_id")
        env_id = job.get("environment_id")
        
        # Check project mapping
        if project_id and project_id not in project_mapping:
            errors.append(ValidationError(
                "project_mapping",
                f"No target project mapped for source project {project_id}",
                config.job_id
            ))
        
        # Check environment mapping
        if env_id and env_id not in environment_mapping:
            errors.append(ValidationError(
                "environment_mapping",
                f"No target environment mapped for source environment {env_id}",
                config.job_id
            ))
    
    return errors


def validate_with_dbt_jobs_as_code(yaml_content: str) -> JACValidationResult:
    """Validate YAML using dbt-jobs-as-code's native validation.
    
    This function writes the YAML to a temp file and uses dbt-jobs-as-code's
    loader to validate it against the official schema.
    
    Args:
        yaml_content: The YAML content to validate
        
    Returns:
        JACValidationResult with validation details
    """
    if not _DBT_JOBS_AS_CODE_AVAILABLE:
        return JACValidationResult(
            is_valid=False,
            errors=["dbt-jobs-as-code is not installed. Install it with: pip install dbt-jobs-as-code"],
            warnings=[],
            job_count=0,
            validated_with_jac=False,
        )
    
    errors: list[str] = []
    warnings: list[str] = []
    job_count = 0
    
    try:
        # Write YAML to a temp file for dbt-jobs-as-code to load
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as tmp_file:
            tmp_file.write(yaml_content)
            tmp_path = tmp_file.name
        
        try:
            # Use dbt-jobs-as-code's loader to validate
            config = load_job_configuration([tmp_path], vars_file=None)
            
            # Count jobs
            job_count = len(config.jobs) if config.jobs else 0
            
            # Validate each job individually for detailed errors
            for identifier, job in (config.jobs or {}).items():
                # The loader already validates via Pydantic, but we can
                # add additional checks here if needed
                
                # Check for potential issues
                if job.triggers.schedule and not job.schedule.cron:
                    warnings.append(
                        f"Job '{identifier}': Schedule trigger enabled but no cron expression"
                    )
                
                if job.linked_id and job.linked_id <= 0:
                    warnings.append(
                        f"Job '{identifier}': linked_id should be a positive integer"
                    )
                    
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
    except LoadingJobsYAMLError as e:
        errors.append(f"YAML loading error: {str(e)}")
    except PydanticValidationError as e:
        # Parse Pydantic validation errors into readable messages
        for error in e.errors():
            loc = " -> ".join(str(x) for x in error["loc"])
            msg = error["msg"]
            errors.append(f"{loc}: {msg}")
    except Exception as e:
        errors.append(f"Validation error: {str(e)}")
    
    return JACValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        job_count=job_count,
        validated_with_jac=True,
    )


def validate_yaml_basic(yaml_content: str) -> JACValidationResult:
    """Basic YAML validation without dbt-jobs-as-code.
    
    This provides a fallback validation using PyYAML and basic schema checks.
    
    Args:
        yaml_content: The YAML content to validate
        
    Returns:
        JACValidationResult with validation details
    """
    import yaml as pyyaml
    
    errors: list[str] = []
    warnings: list[str] = []
    job_count = 0
    
    try:
        data = pyyaml.safe_load(yaml_content)
        
        if not isinstance(data, dict):
            errors.append("Root must be a dictionary")
            return JACValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                job_count=0,
                validated_with_jac=False,
            )
        
        if "jobs" not in data:
            errors.append("Missing 'jobs' key")
            return JACValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                job_count=0,
                validated_with_jac=False,
            )
        
        jobs = data.get("jobs", {})
        if not isinstance(jobs, dict):
            errors.append("'jobs' must be a dictionary")
            return JACValidationResult(
                is_valid=False,
                errors=errors,
                warnings=warnings,
                job_count=0,
                validated_with_jac=False,
            )
        
        job_count = len(jobs)
        
        # Validate each job
        required_fields = [
            "account_id", "project_id", "environment_id", "name",
            "settings", "execute_steps", "schedule", "triggers"
        ]
        
        for identifier, job in jobs.items():
            if not isinstance(job, dict):
                errors.append(f"Job '{identifier}': must be a dictionary")
                continue
            
            # Check required fields
            for field in required_fields:
                if field not in job:
                    errors.append(f"Job '{identifier}': missing required field '{field}'")
            
            # Check settings structure
            settings = job.get("settings", {})
            if isinstance(settings, dict):
                if "threads" not in settings:
                    warnings.append(f"Job '{identifier}': missing 'threads' in settings")
                if "target_name" not in settings:
                    warnings.append(f"Job '{identifier}': missing 'target_name' in settings")
            
            # Check triggers structure
            triggers = job.get("triggers", {})
            if isinstance(triggers, dict):
                trigger_fields = ["github_webhook", "git_provider_webhook", "schedule", "on_merge"]
                for tf in trigger_fields:
                    if tf not in triggers:
                        warnings.append(f"Job '{identifier}': missing '{tf}' in triggers")
            
            # Check for linked_id in adopt workflow
            if "linked_id" in job:
                linked_id = job.get("linked_id")
                if not isinstance(linked_id, int) or linked_id <= 0:
                    errors.append(f"Job '{identifier}': linked_id must be a positive integer")
                    
    except Exception as e:
        errors.append(f"YAML parsing error: {str(e)}")
    
    return JACValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        job_count=job_count,
        validated_with_jac=False,
    )


def validate_yaml_full(yaml_content: str, prefer_jac: bool = True) -> JACValidationResult:
    """Validate YAML with best available method.
    
    Uses dbt-jobs-as-code if available and preferred, otherwise falls back
    to basic validation.
    
    Args:
        yaml_content: The YAML content to validate
        prefer_jac: Whether to prefer dbt-jobs-as-code validation
        
    Returns:
        JACValidationResult with validation details
    """
    if prefer_jac and _DBT_JOBS_AS_CODE_AVAILABLE:
        return validate_with_dbt_jobs_as_code(yaml_content)
    else:
        return validate_yaml_basic(yaml_content)
