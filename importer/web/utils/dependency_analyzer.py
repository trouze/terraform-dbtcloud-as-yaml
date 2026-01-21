"""Analyze resource dependencies for cloning operations."""

from dataclasses import dataclass, field
from typing import Any, Optional, List


@dataclass
class DependencyInfo:
    """Information about a resource's dependencies."""
    
    key: str
    name: str
    resource_type: str
    dbt_id: Optional[int] = None
    is_required: bool = False  # Whether this dependency is required
    required_reason: str = ""  # Why it's required (e.g., "Job requires execution environment")
    children: List["DependencyInfo"] = field(default_factory=list)


# Resource type hierarchy - what can contain what
RESOURCE_HIERARCHY = {
    "ACC": ["PRJ", "CON", "REP", "TOK", "GRP", "NOT", "WEB", "PLE"],  # Account contains these
    "PRJ": ["ENV", "JOB", "VAR"],  # Project contains environments, jobs, env vars
    "ENV": ["VAR"],  # Environment can have env-specific variable values
    "JOB": [],  # Jobs are leaf nodes
}

# Dependencies between resource types
RESOURCE_DEPENDENCIES = {
    "JOB": {
        "ENV": {
            "field": "environment_id",
            "required": True,
            "reason": "Job requires an execution environment",
        },
        "JOB": {
            "field": "job_completion_trigger_condition.job_id",
            "required": False,
            "reason": "Job triggered by completion of another job",
        },
    },
    "ENV": {
        "CON": {
            "field": "connection_id",
            "required": False,
            "reason": "Environment uses this connection",
        },
        "REP": {
            "field": "repository_id",
            "required": False,
            "reason": "Environment uses this repository",
        },
    },
    "VAR": {
        "ENV": {
            "field": "environment_id",
            "required": False,
            "reason": "Variable value scoped to environment",
        },
    },
}


def get_parent_key(item: dict) -> Optional[str]:
    """Get the parent key for an item, if any."""
    return item.get("parent_key")


def get_project_key(item: dict) -> Optional[str]:
    """Get the project key for an item."""
    # Items within a project have a parent_key to the project
    # Or they might have project_id
    parent_key = item.get("parent_key", "")
    if parent_key and parent_key.startswith("PRJ:"):
        return parent_key
    
    project_id = item.get("project_id")
    if project_id:
        return f"PRJ:{project_id}"
    
    return None


def build_dependency_tree(
    source_key: str,
    all_items: list[dict],
    include_children: bool = True,
    include_references: bool = True,
) -> DependencyInfo:
    """Build a dependency tree for a resource.
    
    Args:
        source_key: Key of the source resource
        all_items: All report items from the account
        include_children: Whether to include child resources (contained within)
        include_references: Whether to include referenced resources (used by)
        
    Returns:
        DependencyInfo tree for the resource
    """
    # Build lookup maps
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    items_by_parent = {}
    for item in all_items:
        parent = item.get("parent_key")
        if parent:
            if parent not in items_by_parent:
                items_by_parent[parent] = []
            items_by_parent[parent].append(item)
    
    source_item = items_by_key.get(source_key)
    if not source_item:
        return DependencyInfo(key=source_key, name="Unknown", resource_type="")
    
    root = DependencyInfo(
        key=source_key,
        name=source_item.get("name", ""),
        resource_type=source_item.get("element_type_code", ""),
        dbt_id=source_item.get("dbt_id"),
    )
    
    # Add children (resources contained within this one)
    if include_children:
        children = items_by_parent.get(source_key, [])
        for child in children:
            child_key = child.get("key")
            if child_key:
                child_info = build_dependency_tree(
                    child_key, all_items, include_children=True, include_references=False
                )
                root.children.append(child_info)
    
    # Add references (resources this one depends on)
    if include_references:
        source_type = source_item.get("element_type_code", "")
        deps = RESOURCE_DEPENDENCIES.get(source_type, {})
        
        for dep_type, dep_info in deps.items():
            dep_field = dep_info["field"]
            
            # Get the referenced ID from the source item
            ref_id = _get_nested_field(source_item, dep_field)
            if not ref_id:
                continue
            
            # Find the referenced item
            for item in all_items:
                if (
                    item.get("element_type_code") == dep_type
                    and item.get("dbt_id") == ref_id
                ):
                    ref_info = DependencyInfo(
                        key=item.get("key", ""),
                        name=item.get("name", ""),
                        resource_type=dep_type,
                        dbt_id=item.get("dbt_id"),
                        is_required=dep_info["required"],
                        required_reason=dep_info["reason"],
                    )
                    root.children.append(ref_info)
                    break
    
    return root


def _get_nested_field(item: dict, field_path: str) -> Any:
    """Get a nested field value using dot notation."""
    parts = field_path.split(".")
    value = item
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
    return value


def get_children_by_type(
    source_key: str,
    all_items: list[dict],
) -> dict[str, list[dict]]:
    """Get child resources grouped by type.
    
    Args:
        source_key: Key of the parent resource
        all_items: All report items
        
    Returns:
        Dict mapping type codes to lists of child items
    """
    result: dict[str, list[dict]] = {}
    
    for item in all_items:
        if item.get("parent_key") == source_key:
            type_code = item.get("element_type_code", "")
            if type_code not in result:
                result[type_code] = []
            result[type_code].append(item)
    
    return result


def get_required_dependencies(
    source_item: dict,
    all_items: list[dict],
) -> list[dict]:
    """Get required dependencies for a resource.
    
    Args:
        source_item: The source resource item
        all_items: All report items
        
    Returns:
        List of required dependency items
    """
    result = []
    source_type = source_item.get("element_type_code", "")
    deps = RESOURCE_DEPENDENCIES.get(source_type, {})
    
    items_by_type_id = {}
    for item in all_items:
        type_code = item.get("element_type_code", "")
        dbt_id = item.get("dbt_id")
        if dbt_id:
            items_by_type_id[(type_code, dbt_id)] = item
    
    for dep_type, dep_info in deps.items():
        if not dep_info["required"]:
            continue
        
        dep_field = dep_info["field"]
        ref_id = _get_nested_field(source_item, dep_field)
        
        if ref_id:
            ref_item = items_by_type_id.get((dep_type, ref_id))
            if ref_item:
                result.append({
                    **ref_item,
                    "_required_reason": dep_info["reason"],
                })
    
    return result


def validate_clone_dependencies(
    source_key: str,
    selected_dependent_keys: set[str],
    all_items: list[dict],
) -> list[str]:
    """Validate that a clone configuration has all required dependencies.
    
    Args:
        source_key: Key of the resource being cloned
        selected_dependent_keys: Keys of dependents user selected to include
        all_items: All report items
        
    Returns:
        List of validation error messages
    """
    errors = []
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    
    source_item = items_by_key.get(source_key)
    if not source_item:
        return [f"Source resource not found: {source_key}"]
    
    required = get_required_dependencies(source_item, all_items)
    for req in required:
        req_key = req.get("key")
        if req_key and req_key not in selected_dependent_keys:
            errors.append(
                f"Missing required dependency: {req.get('name')} ({req.get('_required_reason')})"
            )
    
    return errors


def detect_circular_dependencies(
    clone_configs: list[dict],
    all_items: list[dict],
) -> list[str]:
    """Detect circular dependencies in clone configurations.
    
    Args:
        clone_configs: List of clone configurations
        all_items: All report items
        
    Returns:
        List of warning messages about circular dependencies
    """
    warnings = []
    
    # Build a graph of job trigger dependencies
    items_by_key = {item.get("key"): item for item in all_items if item.get("key")}
    
    # Only check jobs for trigger cycles
    job_triggers: dict[str, list[str]] = {}
    
    for item in all_items:
        if item.get("element_type_code") != "JOB":
            continue
        
        key = item.get("key", "")
        triggers = item.get("job_completion_trigger_condition", {})
        trigger_job_id = triggers.get("job_id") if isinstance(triggers, dict) else None
        
        if trigger_job_id:
            # Find the triggering job's key
            for other in all_items:
                if (
                    other.get("element_type_code") == "JOB"
                    and other.get("dbt_id") == trigger_job_id
                ):
                    if key not in job_triggers:
                        job_triggers[key] = []
                    job_triggers[key].append(other.get("key", ""))
                    break
    
    # Detect cycles using DFS
    def find_cycle(start: str, visited: set, path: list) -> Optional[list]:
        if start in path:
            cycle_start = path.index(start)
            return path[cycle_start:] + [start]
        
        if start in visited:
            return None
        
        visited.add(start)
        path.append(start)
        
        for next_key in job_triggers.get(start, []):
            cycle = find_cycle(next_key, visited, path)
            if cycle:
                return cycle
        
        path.pop()
        return None
    
    # Check each job that's being cloned
    {c.get("source_key") for c in clone_configs}
    for config in clone_configs:
        source_key = config.get("source_key", "")
        source_item = items_by_key.get(source_key)
        
        if source_item and source_item.get("element_type_code") == "JOB":
            cycle = find_cycle(source_key, set(), [])
            if cycle:
                cycle_names = [
                    items_by_key.get(k, {}).get("name", k) for k in cycle
                ]
                warnings.append(
                    f"Circular trigger dependency detected: {' → '.join(cycle_names)}"
                )
    
    return warnings
