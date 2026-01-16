"""Target resource mapping file utilities for load/save/validate."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import yaml


@dataclass
class MappingValidationError:
    """A single validation error in the mapping file."""
    
    message: str
    mapping_index: Optional[int] = None
    field: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class MappingValidationResult:
    """Result of validating a mapping file."""
    
    valid: bool
    errors: list[MappingValidationError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    
    def add_error(
        self,
        message: str,
        mapping_index: Optional[int] = None,
        field: Optional[str] = None,
        suggestion: Optional[str] = None,
    ) -> None:
        """Add a validation error."""
        self.errors.append(MappingValidationError(
            message=message,
            mapping_index=mapping_index,
            field=field,
            suggestion=suggestion,
        ))
        self.valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a validation warning."""
        self.warnings.append(message)


@dataclass
class TargetResourceMapping:
    """Target resource mapping file schema."""
    
    version: int = 1
    metadata: dict = field(default_factory=dict)
    mappings: list[dict] = field(default_factory=list)
    
    @classmethod
    def create(
        cls,
        source_account_id: str,
        target_account_id: str,
        mappings: list[dict],
    ) -> "TargetResourceMapping":
        """Create a new mapping file with metadata."""
        return cls(
            version=1,
            metadata={
                "source_account_id": source_account_id,
                "target_account_id": target_account_id,
                "created_at": datetime.utcnow().isoformat() + "Z",
                "created_by": "web-ui",
            },
            mappings=mappings,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "metadata": self.metadata,
            "mappings": self.mappings,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TargetResourceMapping":
        """Create from dictionary."""
        return cls(
            version=data.get("version", 1),
            metadata=data.get("metadata", {}),
            mappings=data.get("mappings", []),
        )


def load_mapping_file(path: Union[str, Path]) -> tuple[Optional[TargetResourceMapping], Optional[str]]:
    """Load a target resource mapping file.
    
    Args:
        path: Path to the mapping file (YAML or JSON)
        
    Returns:
        Tuple of (mapping, error_message)
    """
    path = Path(path)
    
    if not path.exists():
        return None, f"File not found: {path}"
    
    try:
        content = path.read_text(encoding="utf-8")
        
        # Try YAML first (also handles JSON)
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            return None, f"Invalid YAML/JSON: {e}"
        
        if not isinstance(data, dict):
            return None, "Mapping file must be a YAML/JSON object"
        
        mapping = TargetResourceMapping.from_dict(data)
        return mapping, None
        
    except Exception as e:
        return None, f"Failed to read file: {e}"


def save_mapping_file(
    mapping: TargetResourceMapping,
    path: Union[str, Path],
    format: str = "yaml",
) -> Optional[str]:
    """Save a target resource mapping file.
    
    Args:
        mapping: The mapping to save
        path: Path to save to
        format: "yaml" or "json"
        
    Returns:
        Error message if failed, None on success
    """
    path = Path(path)
    
    try:
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = mapping.to_dict()
        
        if format == "json":
            content = json.dumps(data, indent=2)
        else:
            content = yaml.dump(data, default_flow_style=False, sort_keys=False)
        
        path.write_text(content, encoding="utf-8")
        return None
        
    except Exception as e:
        return f"Failed to save file: {e}"


def validate_mapping_file(
    mapping: TargetResourceMapping,
    source_report_items: list[dict],
    target_report_items: list[dict],
) -> MappingValidationResult:
    """Validate a mapping file against source and target data.
    
    Checks:
    - All source references exist in source data
    - All target references exist in target data
    - Resource types match between source and target
    - No duplicate source mappings
    - No duplicate target mappings
    
    Args:
        mapping: The mapping file to validate
        source_report_items: Report items from source fetch
        target_report_items: Report items from target fetch
        
    Returns:
        Validation result with errors and warnings
    """
    result = MappingValidationResult(valid=True)
    
    # Build lookup indexes
    source_by_key = {item.get("key"): item for item in source_report_items}
    target_by_id = {item.get("dbt_id"): item for item in target_report_items}
    
    # Track duplicates
    seen_source_keys: set[str] = set()
    seen_target_ids: set[int] = set()
    
    for idx, m in enumerate(mapping.mappings):
        source_key = m.get("source_key", "")
        target_id = m.get("target_id")
        resource_type = m.get("resource_type", "")
        
        # Check required fields
        if not source_key:
            result.add_error(
                "Missing source_key",
                mapping_index=idx,
                field="source_key",
            )
            continue
        
        if target_id is None:
            result.add_error(
                "Missing target_id",
                mapping_index=idx,
                field="target_id",
            )
            continue
        
        # Check source exists
        if source_key not in source_by_key:
            result.add_error(
                f"Source key '{source_key}' not found in source data",
                mapping_index=idx,
                field="source_key",
            )
        
        # Check target exists
        if target_id not in target_by_id:
            # Try to find similar IDs for suggestion
            similar_ids = [
                tid for tid in target_by_id.keys()
                if tid and abs(tid - target_id) < 100
            ]
            suggestion = f"Did you mean: {similar_ids[0]}?" if similar_ids else None
            
            result.add_error(
                f"Target ID {target_id} not found in target data",
                mapping_index=idx,
                field="target_id",
                suggestion=suggestion,
            )
        
        # Check type match
        source_item = source_by_key.get(source_key)
        target_item = target_by_id.get(target_id)
        
        if source_item and target_item:
            source_type = source_item.get("element_type_code", "")
            target_type = target_item.get("element_type_code", "")
            
            if source_type != target_type:
                result.add_error(
                    f"Type mismatch: source is '{source_type}', target is '{target_type}'",
                    mapping_index=idx,
                )
            
            # Warn if declared type doesn't match actual
            if resource_type and resource_type != source_type:
                result.add_warning(
                    f"Mapping {idx}: declared resource_type '{resource_type}' "
                    f"doesn't match actual source type '{source_type}'"
                )
        
        # Check for duplicate source mappings
        if source_key in seen_source_keys:
            result.add_error(
                f"Duplicate source mapping: '{source_key}' is mapped multiple times",
                mapping_index=idx,
                field="source_key",
            )
        seen_source_keys.add(source_key)
        
        # Check for duplicate target mappings
        if target_id in seen_target_ids:
            result.add_error(
                f"Duplicate target mapping: ID {target_id} is claimed by multiple sources",
                mapping_index=idx,
                field="target_id",
            )
        seen_target_ids.add(target_id)
    
    return result


def create_mapping_from_confirmations(
    confirmed_mappings: list[dict],
    source_account_id: str,
    target_account_id: str,
) -> TargetResourceMapping:
    """Create a TargetResourceMapping from confirmed mappings in the UI.
    
    Args:
        confirmed_mappings: List of mapping dicts from the UI
        source_account_id: Source account ID for metadata
        target_account_id: Target account ID for metadata
        
    Returns:
        TargetResourceMapping ready to save
    """
    # Normalize the mapping format
    normalized_mappings = []
    for m in confirmed_mappings:
        normalized = {
            "resource_type": m.get("resource_type", ""),
            "source_name": m.get("source_name", ""),
            "source_key": m.get("source_key", ""),
            "target_id": m.get("target_id", 0),
            "target_name": m.get("target_name", ""),
            "match_type": m.get("match_type", "manual"),
        }
        normalized_mappings.append(normalized)
    
    return TargetResourceMapping.create(
        source_account_id=source_account_id,
        target_account_id=target_account_id,
        mappings=normalized_mappings,
    )


def get_mapping_summary(mapping: TargetResourceMapping) -> dict:
    """Get a summary of a mapping file.
    
    Args:
        mapping: The mapping to summarize
        
    Returns:
        Dictionary with summary stats
    """
    by_type: dict[str, int] = {}
    by_match_type: dict[str, int] = {}
    
    for m in mapping.mappings:
        resource_type = m.get("resource_type", "unknown")
        match_type = m.get("match_type", "unknown")
        
        by_type[resource_type] = by_type.get(resource_type, 0) + 1
        by_match_type[match_type] = by_match_type.get(match_type, 0) + 1
    
    return {
        "total_mappings": len(mapping.mappings),
        "by_resource_type": by_type,
        "by_match_type": by_match_type,
        "source_account_id": mapping.metadata.get("source_account_id", ""),
        "target_account_id": mapping.metadata.get("target_account_id", ""),
        "created_at": mapping.metadata.get("created_at", ""),
    }
