"""Terraform import utilities for importing existing resources into state."""

import asyncio
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional, Union


@dataclass
class ImportResult:
    """Result of a single resource import operation."""
    
    resource_address: str
    target_id: str
    source_key: str
    resource_type: str
    status: str = "pending"  # "pending", "importing", "success", "failed", "skipped"
    error_message: Optional[str] = None
    duration_ms: Optional[int] = None


@dataclass
class ImportSummary:
    """Summary of import operation results."""
    
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    duration_ms: int = 0
    results: list[ImportResult] = field(default_factory=list)


# Resource type to Terraform resource type mapping
RESOURCE_TYPE_TO_TF = {
    "PRJ": "dbtcloud_project",
    "ENV": "dbtcloud_environment",
    "JOB": "dbtcloud_job",
    "CON": "dbtcloud_global_connection",
    "REP": "dbtcloud_repository",
    "TOK": "dbtcloud_service_token",
    "GRP": "dbtcloud_group",
    "NOT": "dbtcloud_notification",
    "WEB": "dbtcloud_webhook",
    "VAR": "dbtcloud_environment_variable",
}


def get_terraform_resource_address(
    source_key: str,
    resource_type: str,
    module_name: str = "dbt_cloud",
) -> str:
    """Generate a Terraform resource address from a source key.
    
    Args:
        source_key: The source entity key (e.g., "project__my_project")
        resource_type: The resource type code (e.g., "PRJ")
        module_name: The Terraform module name
        
    Returns:
        Terraform resource address (e.g., "module.dbt_cloud.dbtcloud_project.my_project")
    """
    tf_type = RESOURCE_TYPE_TO_TF.get(resource_type, "dbtcloud_unknown")
    
    # Convert source key to resource name
    # Source key format: "type__name" or "type__parent__name"
    # We just need the last part, sanitized for Terraform
    parts = source_key.split("__")
    resource_name = parts[-1] if parts else source_key
    
    # Sanitize for Terraform identifier
    resource_name = re.sub(r'[^a-zA-Z0-9_]', '_', resource_name.lower())
    resource_name = re.sub(r'_+', '_', resource_name)  # Collapse multiple underscores
    resource_name = resource_name.strip('_')
    
    if not resource_name:
        resource_name = "resource"
    
    return f"module.{module_name}.{tf_type}.{resource_name}"


def generate_import_blocks(
    mappings: list[dict],
    module_name: str = "dbt_cloud",
) -> str:
    """Generate Terraform 1.5+ import blocks from mappings.
    
    Args:
        mappings: List of mapping dictionaries with source_key, target_id, resource_type
        module_name: The Terraform module name
        
    Returns:
        Content for imports.tf file with import {} blocks
    """
    blocks = []
    
    # Header comment
    blocks.append("# Generated import blocks for existing target resources")
    blocks.append("# Run 'terraform plan' to process these imports")
    blocks.append("")
    
    for mapping in mappings:
        source_key = mapping.get("source_key", "")
        target_id = mapping.get("target_id", "")
        resource_type = mapping.get("resource_type", "")
        source_name = mapping.get("source_name", "")
        
        if not source_key or not target_id:
            continue
        
        # Get the Terraform resource address
        tf_address = get_terraform_resource_address(source_key, resource_type, module_name)
        
        # Add comment with human-readable info
        blocks.append(f"# {source_name} -> Target ID {target_id}")
        blocks.append(f"import {{")
        blocks.append(f'  to = {tf_address}')
        blocks.append(f'  id = "{target_id}"')
        blocks.append(f"}}")
        blocks.append("")
    
    return "\n".join(blocks)


def generate_import_commands(
    mappings: list[dict],
    module_name: str = "dbt_cloud",
) -> list[tuple[str, str, str, str]]:
    """Generate legacy terraform import commands.
    
    Args:
        mappings: List of mapping dictionaries
        module_name: The Terraform module name
        
    Returns:
        List of (resource_address, import_id, source_key, resource_type) tuples
    """
    commands = []
    
    for mapping in mappings:
        source_key = mapping.get("source_key", "")
        target_id = mapping.get("target_id", "")
        resource_type = mapping.get("resource_type", "")
        
        if not source_key or not target_id:
            continue
        
        tf_address = get_terraform_resource_address(source_key, resource_type, module_name)
        commands.append((tf_address, str(target_id), source_key, resource_type))
    
    return commands


async def detect_terraform_version(cwd: Union[str, Path]) -> tuple[Optional[tuple[int, int, int]], Optional[str]]:
    """Detect installed Terraform version.
    
    Args:
        cwd: Working directory
        
    Returns:
        Tuple of (version_tuple, error_message)
        version_tuple is (major, minor, patch) or None if error
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "terraform", "version", "-json",
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            # Try without -json flag for older versions
            process2 = await asyncio.create_subprocess_exec(
                "terraform", "version",
                cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout2, _ = await process2.communicate()
            
            # Parse version from "Terraform v1.5.0"
            match = re.search(r'v(\d+)\.(\d+)\.(\d+)', stdout2.decode())
            if match:
                return (int(match.group(1)), int(match.group(2)), int(match.group(3))), None
            return None, f"Could not parse Terraform version"
        
        data = json.loads(stdout.decode())
        version_str = data.get("terraform_version", "")
        
        # Parse version string "1.5.0"
        match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3))), None
        
        return None, f"Could not parse version: {version_str}"
        
    except FileNotFoundError:
        return None, "Terraform not found. Please install Terraform."
    except Exception as e:
        return None, f"Error detecting Terraform version: {e}"


def supports_import_blocks(version: tuple[int, int, int]) -> bool:
    """Check if Terraform version supports import {} blocks.
    
    Import blocks were added in Terraform 1.5.0.
    
    Args:
        version: (major, minor, patch) tuple
        
    Returns:
        True if import blocks are supported
    """
    return version >= (1, 5, 0)


async def run_terraform_import(
    resource_address: str,
    import_id: str,
    cwd: Union[str, Path],
    on_output: Optional[Callable[[str], None]] = None,
) -> tuple[bool, str]:
    """Run a single terraform import command.
    
    Args:
        resource_address: The Terraform resource address
        import_id: The ID to import
        cwd: Working directory
        on_output: Optional callback for output lines
        
    Returns:
        Tuple of (success, output)
    """
    output_lines = []
    
    try:
        process = await asyncio.create_subprocess_exec(
            "terraform", "import", resource_address, import_id,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        
        async for line in process.stdout:
            decoded = line.decode()
            output_lines.append(decoded)
            if on_output:
                on_output(decoded)
        
        await process.wait()
        
        output = "".join(output_lines)
        success = process.returncode == 0
        
        return success, output
        
    except Exception as e:
        return False, str(e)


async def run_import_batch(
    import_commands: list[tuple[str, str, str, str]],
    cwd: Union[str, Path],
    on_progress: Optional[Callable[[ImportResult], None]] = None,
    on_output: Optional[Callable[[str], None]] = None,
) -> ImportSummary:
    """Run a batch of terraform import commands sequentially.
    
    Args:
        import_commands: List of (address, id, source_key, resource_type) tuples
        cwd: Working directory
        on_progress: Callback for progress updates per resource
        on_output: Callback for command output
        
    Returns:
        ImportSummary with results
    """
    summary = ImportSummary(total=len(import_commands))
    start_time = time.time()
    
    for address, import_id, source_key, resource_type in import_commands:
        result = ImportResult(
            resource_address=address,
            target_id=import_id,
            source_key=source_key,
            resource_type=resource_type,
            status="importing",
        )
        
        if on_progress:
            on_progress(result)
        
        import_start = time.time()
        success, output = await run_terraform_import(
            address, import_id, cwd, on_output
        )
        import_duration = int((time.time() - import_start) * 1000)
        
        result.duration_ms = import_duration
        
        if success:
            result.status = "success"
            summary.success += 1
        else:
            result.status = "failed"
            result.error_message = output
            summary.failed += 1
        
        summary.results.append(result)
        
        if on_progress:
            on_progress(result)
    
    summary.duration_ms = int((time.time() - start_time) * 1000)
    return summary


def write_import_blocks_file(
    mappings: list[dict],
    output_dir: Union[str, Path],
    module_name: str = "dbt_cloud",
    filename: str = "imports.tf",
) -> tuple[Optional[Path], Optional[str]]:
    """Write import blocks to a file.
    
    Args:
        mappings: List of mapping dictionaries
        output_dir: Directory to write to
        module_name: Terraform module name
        filename: Output filename
        
    Returns:
        Tuple of (file_path, error_message)
    """
    try:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        content = generate_import_blocks(mappings, module_name)
        file_path = output_dir / filename
        
        file_path.write_text(content, encoding="utf-8")
        return file_path, None
        
    except Exception as e:
        return None, str(e)


def parse_import_errors(output: str) -> dict:
    """Parse Terraform import errors for user-friendly messages.
    
    Args:
        output: Raw Terraform output
        
    Returns:
        Dictionary with error_type and suggestion
    """
    output_lower = output.lower()
    
    if "resource already managed" in output_lower or "already exists in state" in output_lower:
        return {
            "error_type": "already_imported",
            "suggestion": "This resource is already in Terraform state. You can skip it.",
        }
    
    if "not found" in output_lower or "404" in output_lower:
        return {
            "error_type": "not_found",
            "suggestion": "The resource was not found. Check if the Target ID is correct.",
        }
    
    if "unauthorized" in output_lower or "401" in output_lower:
        return {
            "error_type": "auth_error",
            "suggestion": "Authentication failed. Check your target API token permissions.",
        }
    
    if "forbidden" in output_lower or "403" in output_lower:
        return {
            "error_type": "permission_denied",
            "suggestion": "Permission denied. Your token may not have access to this resource.",
        }
    
    return {
        "error_type": "unknown",
        "suggestion": "Check the full error output for details.",
    }
