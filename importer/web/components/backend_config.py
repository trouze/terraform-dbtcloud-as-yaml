"""Terraform backend configuration component for the Deploy page."""

from pathlib import Path
from typing import Callable, Dict, Optional, Any

from nicegui import ui

# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_NAVY = "#192847"

# Backend type definitions with their required/optional fields
BACKEND_SCHEMAS = {
    "local": {
        "name": "Local",
        "description": "Store state in a local file (default, not recommended for production)",
        "fields": {
            "path": {
                "label": "State File Path",
                "type": "text",
                "required": False,
                "default": "terraform.tfstate",
                "description": "Path to the state file",
            },
        },
    },
    "s3": {
        "name": "Amazon S3",
        "description": "Store state in an S3 bucket with optional locking via DynamoDB",
        "fields": {
            "bucket": {
                "label": "S3 Bucket Name",
                "type": "text",
                "required": True,
                "description": "Name of the S3 bucket",
            },
            "key": {
                "label": "State File Key",
                "type": "text",
                "required": True,
                "default": "terraform.tfstate",
                "description": "Path to the state file within the bucket",
            },
            "region": {
                "label": "AWS Region",
                "type": "text",
                "required": True,
                "default": "us-east-1",
                "description": "AWS region where the bucket is located",
            },
            "encrypt": {
                "label": "Encrypt State",
                "type": "boolean",
                "required": False,
                "default": True,
                "description": "Enable server-side encryption",
            },
            "dynamodb_table": {
                "label": "DynamoDB Lock Table",
                "type": "text",
                "required": False,
                "description": "DynamoDB table for state locking (optional)",
            },
        },
    },
    "gcs": {
        "name": "Google Cloud Storage",
        "description": "Store state in a GCS bucket",
        "fields": {
            "bucket": {
                "label": "GCS Bucket Name",
                "type": "text",
                "required": True,
                "description": "Name of the GCS bucket",
            },
            "prefix": {
                "label": "State File Prefix",
                "type": "text",
                "required": False,
                "default": "terraform/state",
                "description": "Path prefix within the bucket",
            },
        },
    },
    "azurerm": {
        "name": "Azure Blob Storage",
        "description": "Store state in Azure Blob Storage",
        "fields": {
            "resource_group_name": {
                "label": "Resource Group",
                "type": "text",
                "required": True,
                "description": "Azure resource group name",
            },
            "storage_account_name": {
                "label": "Storage Account",
                "type": "text",
                "required": True,
                "description": "Azure storage account name",
            },
            "container_name": {
                "label": "Container Name",
                "type": "text",
                "required": True,
                "description": "Blob container name",
            },
            "key": {
                "label": "State File Name",
                "type": "text",
                "required": True,
                "default": "terraform.tfstate",
                "description": "Name of the state file blob",
            },
        },
    },
}


def create_backend_config_section(
    backend_config: Dict[str, Any],
    on_config_change: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> None:
    """Create the Terraform backend configuration section.
    
    Args:
        backend_config: Dictionary to store backend configuration
        on_config_change: Callback when configuration changes
    """
    with ui.card().classes("w-full"):
        with ui.row().classes("items-center gap-2 mb-4"):
            ui.icon("storage", size="md").style(f"color: {DBT_ORANGE};")
            ui.label("Terraform Backend").classes("text-lg font-semibold")
        
        ui.label(
            "Configure where Terraform stores its state file. "
            "Remote backends are recommended for team environments."
        ).classes("text-sm text-slate-600 dark:text-slate-400 mb-4")
        
        # Use existing backend.tf option
        use_existing = ui.checkbox(
            "Use existing backend.tf file",
            value=backend_config.get("use_existing", False),
        )
        use_existing.on("update:model-value", lambda e: _update_config(
            backend_config, "use_existing", e.args, on_config_change
        ))
        
        # Backend type selector
        with ui.column().classes("w-full gap-4 mt-4").bind_visibility_from(use_existing, "value", value=False):
            ui.label("Backend Type").classes("text-sm font-medium")
            
            backend_type = ui.radio(
                options={
                    "local": "Local (default)",
                    "s3": "Amazon S3",
                    "gcs": "Google Cloud Storage",
                    "azurerm": "Azure Blob Storage",
                },
                value=backend_config.get("type", "local"),
            ).props("inline")
            backend_type.on("update:model-value", lambda e: _on_backend_type_change(
                backend_config, e.args, on_config_change, fields_container
            ))
            
            # Dynamic fields container
            fields_container = ui.column().classes("w-full gap-3 mt-4")
            
            # Render initial fields
            with fields_container:
                _render_backend_fields(
                    backend_config.get("type", "local"),
                    backend_config,
                    on_config_change,
                )


def _on_backend_type_change(
    backend_config: Dict[str, Any],
    value: str,
    on_config_change: Optional[Callable[[Dict[str, Any]], None]],
    fields_container,
) -> None:
    """Handle backend type change.
    
    Args:
        backend_config: Backend configuration dictionary
        value: New backend type
        on_config_change: Callback for config changes
        fields_container: Container for backend fields
    """
    backend_config["type"] = value
    
    # Clear existing fields and re-render
    fields_container.clear()
    with fields_container:
        _render_backend_fields(value, backend_config, on_config_change)
    
    if on_config_change:
        on_config_change(backend_config)


def _render_backend_fields(
    backend_type: str,
    backend_config: Dict[str, Any],
    on_config_change: Optional[Callable[[Dict[str, Any]], None]],
) -> None:
    """Render fields for the selected backend type.
    
    Args:
        backend_type: Selected backend type
        backend_config: Backend configuration dictionary
        on_config_change: Callback for config changes
    """
    schema = BACKEND_SCHEMAS.get(backend_type)
    if not schema:
        return
    
    # Show backend description
    ui.label(schema["description"]).classes("text-sm text-slate-500 italic mb-2")
    
    if backend_type == "local":
        # Local backend has minimal config
        ui.label("No additional configuration required for local backend.").classes(
            "text-sm text-slate-500"
        )
        return
    
    # Render fields for cloud backends
    fields = schema.get("fields", {})
    for field_name, field_config in fields.items():
        _render_field(
            field_name,
            field_config,
            backend_config,
            on_config_change,
        )


def _render_field(
    field_name: str,
    field_config: Dict[str, Any],
    backend_config: Dict[str, Any],
    on_config_change: Optional[Callable[[Dict[str, Any]], None]],
) -> None:
    """Render a single backend configuration field.
    
    Args:
        field_name: Field identifier
        field_config: Field configuration
        backend_config: Backend configuration dictionary
        on_config_change: Callback for config changes
    """
    label = field_config["label"]
    field_type = field_config.get("type", "text")
    required = field_config.get("required", False)
    default = field_config.get("default", "")
    description = field_config.get("description", "")
    
    # Get current value
    current_value = backend_config.get(field_name, default)
    
    if required:
        label += " *"
    
    with ui.row().classes("w-full items-center gap-2"):
        if field_type == "boolean":
            ui.label(label).classes("w-44 text-sm")
            toggle = ui.switch(value=bool(current_value)).props("dense")
            toggle.on("update:model-value", lambda e, fn=field_name: _update_config(
                backend_config, fn, e.args, on_config_change
            ))
        else:
            ui.label(label).classes("w-44 text-sm")
            input_field = ui.input(
                value=str(current_value) if current_value else "",
                placeholder=description,
            ).props("dense").classes("flex-grow")
            input_field.on("update:model-value", lambda e, fn=field_name: _update_config(
                backend_config, fn, e.args, on_config_change
            ))


def _update_config(
    backend_config: Dict[str, Any],
    field: str,
    value: Any,
    on_config_change: Optional[Callable[[Dict[str, Any]], None]],
) -> None:
    """Update backend configuration.
    
    Args:
        backend_config: Backend configuration dictionary
        field: Field name to update
        value: New value
        on_config_change: Callback for config changes
    """
    backend_config[field] = value
    if on_config_change:
        on_config_change(backend_config)


def generate_backend_tf(backend_config: Dict[str, Any]) -> str:
    """Generate backend.tf content from configuration.
    
    Args:
        backend_config: Backend configuration dictionary
        
    Returns:
        Terraform backend configuration as a string
    """
    if backend_config.get("use_existing", False):
        return ""
    
    backend_type = backend_config.get("type", "local")
    
    if backend_type == "local":
        path = backend_config.get("path", "terraform.tfstate")
        return f'''terraform {{
  backend "local" {{
    path = "{path}"
  }}
}}
'''
    
    elif backend_type == "s3":
        lines = ['terraform {', '  backend "s3" {']
        
        bucket = backend_config.get("bucket", "")
        key = backend_config.get("key", "terraform.tfstate")
        region = backend_config.get("region", "us-east-1")
        encrypt = backend_config.get("encrypt", True)
        dynamodb_table = backend_config.get("dynamodb_table", "")
        
        if bucket:
            lines.append(f'    bucket = "{bucket}"')
        if key:
            lines.append(f'    key    = "{key}"')
        if region:
            lines.append(f'    region = "{region}"')
        if encrypt:
            lines.append('    encrypt = true')
        if dynamodb_table:
            lines.append(f'    dynamodb_table = "{dynamodb_table}"')
        
        lines.extend(['  }', '}'])
        return '\n'.join(lines) + '\n'
    
    elif backend_type == "gcs":
        lines = ['terraform {', '  backend "gcs" {']
        
        bucket = backend_config.get("bucket", "")
        prefix = backend_config.get("prefix", "")
        
        if bucket:
            lines.append(f'    bucket = "{bucket}"')
        if prefix:
            lines.append(f'    prefix = "{prefix}"')
        
        lines.extend(['  }', '}'])
        return '\n'.join(lines) + '\n'
    
    elif backend_type == "azurerm":
        lines = ['terraform {', '  backend "azurerm" {']
        
        resource_group = backend_config.get("resource_group_name", "")
        storage_account = backend_config.get("storage_account_name", "")
        container = backend_config.get("container_name", "")
        key = backend_config.get("key", "terraform.tfstate")
        
        if resource_group:
            lines.append(f'    resource_group_name  = "{resource_group}"')
        if storage_account:
            lines.append(f'    storage_account_name = "{storage_account}"')
        if container:
            lines.append(f'    container_name       = "{container}"')
        if key:
            lines.append(f'    key                  = "{key}"')
        
        lines.extend(['  }', '}'])
        return '\n'.join(lines) + '\n'
    
    return ""


def write_backend_tf(backend_config: Dict[str, Any], output_dir: str) -> Optional[str]:
    """Write backend.tf file to the output directory.
    
    Args:
        backend_config: Backend configuration dictionary
        output_dir: Directory to write the file to
        
    Returns:
        Path to the written file, or None if skipped
    """
    if backend_config.get("use_existing", False):
        return None
    
    content = generate_backend_tf(backend_config)
    if not content:
        return None
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    backend_file = output_path / "backend.tf"
    backend_file.write_text(content)
    
    return str(backend_file)
