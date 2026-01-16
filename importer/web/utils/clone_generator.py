"""Generate cloned resource configurations for Terraform."""

from copy import deepcopy
from typing import Any

from importer.web.state import CloneConfig


# Fields to strip from cloned resources (IDs and timestamps)
STRIP_FIELDS = {
    "id",
    "dbt_id",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
    "account_id",
}

# Fields that reference other resources by ID (need remapping)
REFERENCE_FIELDS = {
    "JOB": {
        "environment_id": "ENV",
        "project_id": "PRJ",
        "job_completion_trigger_condition.job_id": "JOB",
    },
    "ENV": {
        "project_id": "PRJ",
        "connection_id": "CON",
        "repository_id": "REP",
        "credentials_id": "credentials",
    },
    "VAR": {
        "project_id": "PRJ",
        "environment_id": "ENV",
    },
}


def generate_clone_key(original_key: str, clone_name: str) -> str:
    """Generate a unique key for a cloned resource.
    
    Args:
        original_key: Original resource key (e.g., "JOB:123")
        clone_name: New name for the clone
        
    Returns:
        New key like "JOB:clone:Production Job - Copy"
    """
    type_prefix = original_key.split(":")[0] if ":" in original_key else ""
    safe_name = clone_name.replace(":", "_").replace("/", "_")
    return f"{type_prefix}:clone:{safe_name}"


def generate_cloned_resource(
    source_item: dict,
    config: CloneConfig,
    all_items: list[dict],
    id_mapping: dict[int, str],  # old_id -> new_key for remapping references
) -> dict:
    """Generate a cloned resource configuration.
    
    Args:
        source_item: Original resource item
        config: Clone configuration
        all_items: All source items (for reference lookup)
        id_mapping: Mapping of original IDs to new clone keys
        
    Returns:
        New resource item for the clone
    """
    # Deep copy the source item
    cloned = deepcopy(source_item)
    
    # Update name
    cloned["name"] = config.new_name
    
    # Generate new key
    original_key = source_item.get("key", "")
    cloned["key"] = generate_clone_key(original_key, config.new_name)
    
    # Mark as clone
    cloned["_is_clone"] = True
    cloned["_clone_source_key"] = original_key
    
    # Strip ID fields
    for field in STRIP_FIELDS:
        if field in cloned:
            del cloned[field]
    
    # Handle triggers if not included
    if not config.include_triggers:
        if "triggers" in cloned:
            cloned["triggers"] = {
                "schedule": False,
                "on_merge": False,
                "git_provider_webhook": False,
            }
        if "schedule" in cloned:
            del cloned["schedule"]
    
    # Handle credentials if not included
    if not config.include_credentials:
        _strip_credentials(cloned)
    
    # Handle environment variable values
    source_type = source_item.get("element_type_code", "")
    if source_type == "VAR" and not config.include_env_values:
        if "value" in cloned:
            cloned["value"] = ""  # Clear the value
    
    return cloned


def _strip_credentials(item: dict) -> None:
    """Strip credential fields from an item in place."""
    credential_fields = [
        "password",
        "private_key",
        "token",
        "api_key",
        "secret",
        "auth_token",
        "oauth_token",
        "credentials",
    ]
    
    for field in credential_fields:
        if field in item:
            item[field] = "REDACTED"
    
    # Handle nested credential objects
    if "credentials" in item and isinstance(item["credentials"], dict):
        for key in item["credentials"]:
            if any(sens in key.lower() for sens in ["password", "secret", "token", "key"]):
                item["credentials"][key] = "REDACTED"


def generate_cloned_dependent(
    source_item: dict,
    new_name: str,
    parent_clone_config: CloneConfig,
    all_items: list[dict],
) -> dict:
    """Generate a cloned dependent resource.
    
    Args:
        source_item: Original dependent resource item
        new_name: New name for the dependent
        parent_clone_config: Parent's clone configuration
        all_items: All source items
        
    Returns:
        New resource item for the cloned dependent
    """
    cloned = deepcopy(source_item)
    
    # Update name
    cloned["name"] = new_name
    
    # Generate new key
    original_key = source_item.get("key", "")
    cloned["key"] = generate_clone_key(original_key, new_name)
    
    # Mark as clone
    cloned["_is_clone"] = True
    cloned["_clone_source_key"] = original_key
    cloned["_clone_parent_key"] = parent_clone_config.source_key
    
    # Strip ID fields
    for field in STRIP_FIELDS:
        if field in cloned:
            del cloned[field]
    
    # Handle triggers
    source_type = source_item.get("element_type_code", "")
    if source_type == "JOB" and not parent_clone_config.include_triggers:
        if "triggers" in cloned:
            cloned["triggers"] = {
                "schedule": False,
                "on_merge": False,
                "git_provider_webhook": False,
            }
    
    # Handle credentials
    if not parent_clone_config.include_credentials:
        _strip_credentials(cloned)
    
    # Handle env var values
    if source_type == "VAR" and not parent_clone_config.include_env_values:
        if "value" in cloned:
            cloned["value"] = ""
    
    return cloned


def generate_all_clones(
    clone_configs: list[CloneConfig],
    all_items: list[dict],
) -> list[dict]:
    """Generate all cloned resources from clone configurations.
    
    Args:
        clone_configs: List of clone configurations
        all_items: All source items
        
    Returns:
        List of cloned resource items to add to the migration
    """
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    cloned_items = []
    
    # Track ID mappings for reference updates
    id_mapping: dict[int, str] = {}
    
    for config in clone_configs:
        source_item = items_by_key.get(config.source_key)
        if not source_item:
            continue
        
        # Generate the main clone
        cloned = generate_cloned_resource(
            source_item, config, all_items, id_mapping
        )
        cloned_items.append(cloned)
        
        # Track ID mapping
        original_id = source_item.get("dbt_id")
        if original_id:
            id_mapping[original_id] = cloned["key"]
        
        # Generate cloned dependents
        for dep_key in config.include_dependents:
            dep_item = items_by_key.get(dep_key)
            if not dep_item:
                continue
            
            new_name = config.dependent_names.get(
                dep_key,
                f"{dep_item.get('name', '')} - Copy"
            )
            
            cloned_dep = generate_cloned_dependent(
                dep_item, new_name, config, all_items
            )
            cloned_items.append(cloned_dep)
            
            # Track ID mapping for dependent
            dep_original_id = dep_item.get("dbt_id")
            if dep_original_id:
                id_mapping[dep_original_id] = cloned_dep["key"]
    
    # Update references in all cloned items
    for item in cloned_items:
        _update_references(item, id_mapping)
    
    return cloned_items


def _update_references(item: dict, id_mapping: dict[int, str]) -> None:
    """Update resource references in a cloned item to point to other clones.
    
    Args:
        item: Cloned item to update
        id_mapping: Mapping of original IDs to new clone keys
    """
    item_type = item.get("element_type_code", "")
    ref_fields = REFERENCE_FIELDS.get(item_type, {})
    
    for field_path, ref_type in ref_fields.items():
        old_id = _get_nested_value(item, field_path)
        if old_id and old_id in id_mapping:
            # Reference points to another cloned resource
            # Mark it for later resolution
            item[f"_ref_{field_path.replace('.', '_')}"] = {
                "original_id": old_id,
                "clone_key": id_mapping[old_id],
            }


def _get_nested_value(item: dict, path: str) -> Any:
    """Get a nested value from a dict using dot notation."""
    parts = path.split(".")
    value = item
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def get_clone_summary(
    clone_configs: list[CloneConfig],
    all_items: list[dict],
) -> dict:
    """Get a summary of what will be cloned.
    
    Args:
        clone_configs: List of clone configurations
        all_items: All source items
        
    Returns:
        Summary dict with counts and details
    """
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    
    summary = {
        "total_clones": 0,
        "main_resources": 0,
        "dependents": 0,
        "by_type": {},
        "resources": [],
    }
    
    for config in clone_configs:
        source_item = items_by_key.get(config.source_key)
        if not source_item:
            continue
        
        source_type = source_item.get("element_type_code", "")
        
        # Count main resource
        summary["main_resources"] += 1
        summary["total_clones"] += 1
        summary["by_type"][source_type] = summary["by_type"].get(source_type, 0) + 1
        
        summary["resources"].append({
            "source_key": config.source_key,
            "source_name": source_item.get("name"),
            "new_name": config.new_name,
            "type": source_type,
            "is_main": True,
        })
        
        # Count dependents
        for dep_key in config.include_dependents:
            dep_item = items_by_key.get(dep_key)
            if not dep_item:
                continue
            
            dep_type = dep_item.get("element_type_code", "")
            summary["dependents"] += 1
            summary["total_clones"] += 1
            summary["by_type"][dep_type] = summary["by_type"].get(dep_type, 0) + 1
            
            new_name = config.dependent_names.get(
                dep_key,
                f"{dep_item.get('name', '')} - Copy"
            )
            
            summary["resources"].append({
                "source_key": dep_key,
                "source_name": dep_item.get("name"),
                "new_name": new_name,
                "type": dep_type,
                "is_main": False,
                "parent_key": config.source_key,
            })
    
    return summary


def augment_yaml_with_clones(
    yaml_path: str,
    clone_configs: list[CloneConfig],
    report_items: list[dict],
    output_path: str | None = None,
) -> str:
    """Augment a YAML file with cloned resources.
    
    Args:
        yaml_path: Path to the source YAML file
        clone_configs: List of clone configurations
        report_items: Report items from the source account
        output_path: Output path for the augmented YAML. If None, overwrites input.
        
    Returns:
        Path to the output YAML file
    """
    import yaml
    from pathlib import Path
    
    # Load the existing YAML
    yaml_file = Path(yaml_path)
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not clone_configs:
        # No clones to add
        return yaml_path
    
    # Generate cloned items
    cloned_items = generate_all_clones(clone_configs, report_items)
    
    if not cloned_items:
        return yaml_path
    
    # Add cloned items to the appropriate sections
    for item in cloned_items:
        item_type = item.get("element_type_code", "")
        
        # Determine which section to add to
        if item_type == "PRJ":
            if "projects" not in data:
                data["projects"] = []
            # Convert to project format
            proj_data = _item_to_project(item)
            data["projects"].append(proj_data)
            
        elif item_type == "ENV":
            # Environments go under their project
            parent_key = item.get("_clone_parent_key") or item.get("parent_key", "")
            _add_to_project_section(data, parent_key, "environments", _item_to_environment(item))
            
        elif item_type == "JOB":
            parent_key = item.get("_clone_parent_key") or item.get("parent_key", "")
            _add_to_project_section(data, parent_key, "jobs", _item_to_job(item))
            
        elif item_type == "VAR":
            parent_key = item.get("_clone_parent_key") or item.get("parent_key", "")
            _add_to_project_section(data, parent_key, "environment_variables", _item_to_env_var(item))
            
        elif item_type == "CON":
            if "globals" not in data:
                data["globals"] = {}
            if "connections" not in data["globals"]:
                data["globals"]["connections"] = []
            data["globals"]["connections"].append(_item_to_connection(item))
            
        elif item_type == "REP":
            if "globals" not in data:
                data["globals"] = {}
            if "repositories" not in data["globals"]:
                data["globals"]["repositories"] = []
            data["globals"]["repositories"].append(_item_to_repository(item))
    
    # Write to output
    out_file = Path(output_path) if output_path else yaml_file
    with open(out_file, "w", encoding="utf-8") as f:
        # Preserve header comments if possible
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    return str(out_file)


def _add_to_project_section(data: dict, parent_key: str, section: str, item: dict) -> None:
    """Add an item to a project's section in the YAML data."""
    # Find the project by key
    projects = data.get("projects", [])
    for proj in projects:
        proj_key = proj.get("key", "")
        if proj_key == parent_key or proj_key.endswith(parent_key.split(":")[-1]):
            if section not in proj:
                proj[section] = []
            proj[section].append(item)
            return
    
    # If no matching project found, add to first project (fallback)
    if projects:
        if section not in projects[0]:
            projects[0][section] = []
        projects[0][section].append(item)


def _item_to_project(item: dict) -> dict:
    """Convert a report item to project YAML format."""
    return {
        "key": item.get("key", ""),
        "name": item.get("name", ""),
        "description": item.get("description", ""),
        "_is_clone": True,
    }


def _item_to_environment(item: dict) -> dict:
    """Convert a report item to environment YAML format."""
    env = {
        "key": item.get("key", ""),
        "name": item.get("name", ""),
        "dbt_version": item.get("dbt_version", "versionless"),
        "type": item.get("type", "deployment"),
    }
    if item.get("_is_clone"):
        env["_is_clone"] = True
    return env


def _item_to_job(item: dict) -> dict:
    """Convert a report item to job YAML format."""
    job = {
        "key": item.get("key", ""),
        "name": item.get("name", ""),
        "execute_steps": item.get("execute_steps", []),
    }
    
    # Copy other relevant fields
    for field in ["description", "timeout_seconds", "triggers_on_draft_pr"]:
        if field in item:
            job[field] = item[field]
    
    # Handle triggers
    if "triggers" in item:
        job["triggers"] = item["triggers"]
    
    if item.get("_is_clone"):
        job["_is_clone"] = True
    
    return job


def _item_to_env_var(item: dict) -> dict:
    """Convert a report item to environment variable YAML format."""
    var = {
        "key": item.get("key", ""),
        "name": item.get("name", ""),
    }
    if "value" in item:
        var["value"] = item["value"]
    if item.get("_is_clone"):
        var["_is_clone"] = True
    return var


def _item_to_connection(item: dict) -> dict:
    """Convert a report item to connection YAML format."""
    conn = {
        "key": item.get("key", ""),
        "name": item.get("name", ""),
        "type": item.get("type", ""),
    }
    if item.get("_is_clone"):
        conn["_is_clone"] = True
    return conn


def _item_to_repository(item: dict) -> dict:
    """Convert a report item to repository YAML format."""
    repo = {
        "key": item.get("key", ""),
        "remote_url": item.get("remote_url", ""),
    }
    if item.get("_is_clone"):
        repo["_is_clone"] = True
    return repo
