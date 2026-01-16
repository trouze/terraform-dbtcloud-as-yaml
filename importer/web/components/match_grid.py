"""Editable AG Grid component for resource matching."""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
import json
import logging

from nicegui import ui

from importer.web.state import CloneConfig


# Colors
DBT_ORANGE = "#FF694A"
DBT_TEAL = "#047377"


@dataclass
class GridRow:
    """A row in the mapping grid."""
    
    source_key: str
    source_name: str
    source_type: str
    source_id: Optional[int]
    action: str  # "match", "create_new", "skip"
    target_id: str  # String to allow empty/partial input
    target_name: str
    status: str  # "pending", "confirmed", "error", "skipped"
    confidence: str  # "exact_match", "fuzzy", "manual", "none"
    project_name: str = ""
    clone_configured: bool = False  # Whether clone config exists
    clone_name: str = ""  # Name for the clone (if configured)


# Resource type display info
RESOURCE_TYPE_INFO = {
    "ACC": {"name": "Account", "icon": "cloud", "color": "#3B82F6"},
    "CON": {"name": "Connection", "icon": "storage", "color": "#10B981"},
    "REP": {"name": "Repository", "icon": "source", "color": "#8B5CF6"},
    "TOK": {"name": "Service Token", "icon": "key", "color": "#EC4899"},
    "GRP": {"name": "Group", "icon": "group", "color": "#6366F1"},
    "NOT": {"name": "Notification", "icon": "notifications", "color": "#F97316"},
    "WEB": {"name": "Webhook", "icon": "webhook", "color": "#84CC16"},
    "PLE": {"name": "PrivateLink", "icon": "lock", "color": "#14B8A6"},
    "PRJ": {"name": "Project", "icon": "folder", "color": "#F59E0B"},
    "ENV": {"name": "Environment", "icon": "layers", "color": "#06B6D4"},
    "VAR": {"name": "Env Variable", "icon": "code", "color": "#A855F7"},
    "JOB": {"name": "Job", "icon": "schedule", "color": "#EF4444"},
}


def build_grid_data(
    source_items: list[dict],
    target_items: list[dict],
    confirmed_mappings: list[dict],
    rejected_keys: set[str],
    clone_configs: Optional[list[CloneConfig]] = None,
) -> list[dict]:
    """Build grid row data from source/target items and existing mappings.
    
    Args:
        source_items: Report items from source account
        target_items: Report items from target account
        confirmed_mappings: Already confirmed source->target mappings
        rejected_keys: Set of source keys that were rejected
        clone_configs: Optional list of clone configurations
        
    Returns:
        List of row dictionaries for AG Grid
    """
    # Build clone config lookup
    clone_by_key = {}
    if clone_configs:
        for config in clone_configs:
            clone_by_key[config.source_key] = config
    # Build target lookup by (type, name) for auto-matching
    target_by_type_name: dict[tuple[str, str], dict] = {}
    target_by_id: dict[int, dict] = {}
    
    for item in target_items:
        key = (item.get("element_type_code", ""), item.get("name", ""))
        if key not in target_by_type_name:
            target_by_type_name[key] = item
        
        dbt_id = item.get("dbt_id")
        if dbt_id:
            target_by_id[dbt_id] = item
    
    # Build confirmed mapping lookup
    confirmed_by_source_key = {
        m.get("source_key"): m for m in confirmed_mappings
    }
    
    rows = []
    for source in source_items:
        source_key = source.get("key", "")
        source_name = source.get("name", "")
        source_type = source.get("element_type_code", "")
        source_id = source.get("dbt_id")
        project_name = source.get("project_name", "")
        
        # Skip if no key
        if not source_key:
            continue
        
        # Check if this source is already confirmed
        confirmed = confirmed_by_source_key.get(source_key)
        if confirmed:
            target_id = confirmed.get("target_id", "")
            target_name = confirmed.get("target_name", "")
            row = {
                "source_key": source_key,
                "source_name": source_name,
                "source_type": source_type,
                "source_id": source_id,
                "project_name": project_name,
                "action": "match",
                "target_id": str(target_id) if target_id else "",
                "target_name": target_name,
                "status": "confirmed",
                "confidence": confirmed.get("match_type", "manual"),
                "clone_configured": False,
                "clone_name": "",
            }
            rows.append(row)
            continue
        
        # Check if rejected
        if source_key in rejected_keys:
            clone_config = clone_by_key.get(source_key)
            row = {
                "source_key": source_key,
                "source_name": source_name,
                "source_type": source_type,
                "source_id": source_id,
                "project_name": project_name,
                "action": "create_new",
                "target_id": "",
                "target_name": "",
                "status": "skipped",
                "confidence": "none",
                "clone_configured": clone_config is not None,
                "clone_name": clone_config.new_name if clone_config else "",
            }
            rows.append(row)
            continue
        
        # Try auto-match by exact name
        lookup_key = (source_type, source_name)
        clone_config = clone_by_key.get(source_key)
        
        if lookup_key in target_by_type_name:
            target = target_by_type_name[lookup_key]
            row = {
                "source_key": source_key,
                "source_name": source_name,
                "source_type": source_type,
                "source_id": source_id,
                "project_name": project_name,
                "action": "match",
                "target_id": str(target.get("dbt_id", "")),
                "target_name": target.get("name", ""),
                "status": "pending",
                "confidence": "exact_match",
                "clone_configured": False,
                "clone_name": "",
            }
        else:
            # No match found - check for clone config
            row = {
                "source_key": source_key,
                "source_name": source_name,
                "source_type": source_type,
                "source_id": source_id,
                "project_name": project_name,
                "action": "create_new",
                "target_id": "",
                "target_name": "",
                "status": "pending",
                "confidence": "none",
                "clone_configured": clone_config is not None,
                "clone_name": clone_config.new_name if clone_config else "",
            }
        
        rows.append(row)
    
    return rows


def create_match_grid(
    source_items: list[dict],
    target_items: list[dict],
    confirmed_mappings: list[dict],
    rejected_keys: set[str],
    on_row_change: Callable[[dict], None],
    on_accept: Callable[[str], None],
    on_reject: Callable[[str], None],
    on_view_details: Callable[[str], None],
    clone_configs: Optional[list[CloneConfig]] = None,
    on_configure_clone: Optional[Callable[[str], None]] = None,
) -> tuple:
    """Create the editable matching grid.
    
    Args:
        source_items: Report items from source account
        target_items: Report items from target account
        confirmed_mappings: Already confirmed mappings
        rejected_keys: Set of rejected source keys
        on_row_change: Callback when a row value changes
        on_accept: Callback when accept button clicked (source_key)
        on_reject: Callback when reject button clicked (source_key)
        on_view_details: Callback when details button clicked (source_key)
        clone_configs: Optional list of existing clone configurations
        on_configure_clone: Callback when configure clone button clicked (source_key)
        
    Returns:
        Tuple of (grid component, row data list)
    """
    # Build row data
    row_data = build_grid_data(
        source_items, target_items, confirmed_mappings, rejected_keys, clone_configs
    )
    
    # Build target options for autocomplete
    target_options = [
        {
            "id": str(t.get("dbt_id", "")),
            "name": t.get("name", ""),
            "type": t.get("element_type_code", ""),
        }
        for t in target_items if t.get("dbt_id")
    ]
    
    # Column definitions - using proper NiceGUI AG Grid format
    # Note: cellClassRules work better than cellRenderer for styling in NiceGUI
    column_defs = [
        {
            "field": "source_type",
            "headerName": "Type",
            "width": 110,
            # Use valueFormatter for display text
            ":valueFormatter": """params => {
                const types = {
                    'ACC': 'Account', 'CON': 'Connection', 'REP': 'Repository',
                    'TOK': 'Token', 'GRP': 'Group', 'NOT': 'Notify',
                    'WEB': 'Webhook', 'PLE': 'PrivateLink', 'PRJ': 'Project',
                    'ENV': 'Environment', 'VAR': 'EnvVar', 'JOB': 'Job',
                };
                return types[params.value] || params.value;
            }""",
            "cellClassRules": {
                "type-project": "x === 'PRJ'",
                "type-environment": "x === 'ENV'",
                "type-job": "x === 'JOB'",
                "type-connection": "x === 'CON'",
                "type-repository": "x === 'REP'",
                "type-other": "!['PRJ','ENV','JOB','CON','REP'].includes(x)",
            },
        },
        {
            "field": "source_name",
            "headerName": "Source Name",
            "width": 200,
            "filter": "agTextColumnFilter",
            "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
        },
        {
            "field": "source_id",
            "headerName": "Source ID",
            "width": 90,
            "cellStyle": {"fontFamily": "monospace", "fontSize": "11px"},
        },
        {
            "field": "action",
            "headerName": "Action",
            "width": 130,
            "editable": True,
            "cellEditor": "agSelectCellEditor",
            "cellEditorParams": {
                "values": ["match", "create_new", "skip"],
            },
            ":valueFormatter": """params => {
                const labels = {
                    'match': '⛓️ Match',
                    'create_new': '➕ Create New',
                    'skip': '⏭️ Skip',
                };
                return labels[params.value] || params.value;
            }""",
            "cellClassRules": {
                "action-match": "x === 'match'",
                "action-create": "x === 'create_new'",
                "action-skip": "x === 'skip'",
            },
        },
        {
            "field": "target_id",
            "headerName": "Target ID",
            "width": 100,
            "editable": True,
            "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
        },
        {
            "field": "target_name",
            "headerName": "Target Name",
            "width": 180,
            "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
            "cellClassRules": {
                "target-matched": "x && x.length > 0",
                "target-empty": "!x || x.length === 0",
            },
        },
        {
            "field": "status",
            "headerName": "Status",
            "width": 110,
            ":valueFormatter": """params => {
                const labels = {
                    'pending': '⏳ Pending',
                    'confirmed': '✓ Confirmed',
                    'error': '✗ Error',
                    'skipped': '⊘ Skipped',
                };
                return labels[params.value] || params.value;
            }""",
            "cellClassRules": {
                "status-pending": "x === 'pending'",
                "status-confirmed": "x === 'confirmed'",
                "status-error": "x === 'error'",
                "status-skipped": "x === 'skipped'",
            },
        },
        {
            "field": "project_name",
            "headerName": "Project",
            "width": 140,
            "filter": "agTextColumnFilter",
            "cellStyle": {"fontSize": "11px"},
        },
        {
            "field": "clone_name",
            "headerName": "Clone Name",
            "width": 160,
            "cellStyle": {"fontSize": "12px"},
        },
    ]
    
    # Grid options - note: getRowId must be a JS string function for AG Grid
    grid_options = {
        "columnDefs": column_defs,
        "rowData": row_data,
        "pagination": False,  # Show all rows - grid has good scrolling behavior
        "rowHeight": 40,
        "headerHeight": 36,
        "defaultColDef": {
            "resizable": True,
            "sortable": True,
            "filter": True,
        },
        "rowClassRules": {
            "row-confirmed": "data.status === 'confirmed'",
            "row-error": "data.status === 'error'",
            "row-skipped": "data.status === 'skipped' || data.action === 'skip'",
        },
        "stopEditingWhenCellsLoseFocus": True,
        "singleClickEdit": True,
        # Remove getRowId - can cause issues with NiceGUI's AG Grid wrapper
    }
    
    # Create the grid - use balham theme which has both light and dark variants
    # Use flex-grow to fill available space, with min-height for smaller viewports
    grid = ui.aggrid(grid_options, theme="balham").classes("w-full flex-grow").style("height: 100%; min-height: 300px;")
    
    # Handle cell value changes
    def on_cell_changed(e):
        if e.args:
            data = e.args.get("data", {})
            col = e.args.get("colId", "")
            new_val = e.args.get("newValue")
            
            if col == "action":
                # When action changes, update the row
                data["action"] = new_val
                if new_val == "skip":
                    data["status"] = "skipped"
                    data["target_id"] = ""
                    data["target_name"] = ""
                elif new_val == "create_new":
                    data["target_id"] = ""
                    data["target_name"] = ""
                    data["status"] = "pending"
                
                on_row_change(data)
            
            elif col == "target_id":
                # Validate target ID
                data["target_id"] = new_val
                if new_val:
                    # Look up target name
                    target = next(
                        (t for t in target_options if t["id"] == str(new_val)),
                        None
                    )
                    if target:
                        # Validate type matches
                        if target["type"] == data.get("source_type"):
                            data["target_name"] = target["name"]
                            data["status"] = "pending"
                        else:
                            data["target_name"] = f"Type mismatch: {target['type']}"
                            data["status"] = "error"
                    else:
                        data["target_name"] = ""
                        data["status"] = "error"
                else:
                    data["target_name"] = ""
                    data["status"] = "pending" if data.get("action") == "create_new" else "error"
                
                on_row_change(data)
    
    grid.on("cellValueChanged", on_cell_changed)
    
    # Custom CSS for cell class rules and row classes - with dark mode support
    ui.add_css("""
        /* Row background colors based on status */
        .row-confirmed {
            background-color: rgba(16, 185, 129, 0.15) !important;
        }
        .row-error {
            background-color: rgba(239, 68, 68, 0.15) !important;
        }
        .row-skipped {
            background-color: rgba(156, 163, 175, 0.15) !important;
        }
        
        /* Type column colors */
        .type-project { color: #F59E0B !important; font-weight: 600; }
        .type-environment { color: #06B6D4 !important; font-weight: 600; }
        .type-job { color: #EF4444 !important; font-weight: 600; }
        .type-connection { color: #10B981 !important; font-weight: 600; }
        .type-repository { color: #8B5CF6 !important; font-weight: 600; }
        .type-other { color: #6B7280 !important; }
        
        /* Action column colors */
        .action-match { color: #047377 !important; font-weight: 500; }
        .action-create { color: #F59E0B !important; font-weight: 500; }
        .action-skip { color: #6B7280 !important; font-style: italic; }
        
        /* Status column colors */
        .status-pending { color: #D97706 !important; }
        .status-confirmed { color: #059669 !important; font-weight: 600; }
        .status-error { color: #DC2626 !important; font-weight: 600; }
        .status-skipped { color: #6B7280 !important; font-style: italic; }
        
        /* Target column */
        .target-matched { color: #10B981 !important; }
        .target-empty { color: #9CA3AF !important; }
        
        /* Dark mode overrides */
        .dark .row-confirmed,
        .body--dark .row-confirmed {
            background-color: rgba(16, 185, 129, 0.25) !important;
        }
        .dark .row-error,
        .body--dark .row-error {
            background-color: rgba(239, 68, 68, 0.25) !important;
        }
        .dark .row-skipped,
        .body--dark .row-skipped {
            background-color: rgba(156, 163, 175, 0.25) !important;
        }
        
        /* Dark mode type colors - brighter for visibility */
        .dark .type-project, .body--dark .type-project { color: #FBBF24 !important; }
        .dark .type-environment, .body--dark .type-environment { color: #22D3EE !important; }
        .dark .type-job, .body--dark .type-job { color: #F87171 !important; }
        .dark .type-connection, .body--dark .type-connection { color: #34D399 !important; }
        .dark .type-repository, .body--dark .type-repository { color: #A78BFA !important; }
        
        /* Dark mode status colors */
        .dark .status-pending, .body--dark .status-pending { color: #FCD34D !important; }
        .dark .status-confirmed, .body--dark .status-confirmed { color: #6EE7B7 !important; }
        .dark .status-error, .body--dark .status-error { color: #FCA5A5 !important; }
        
        /* Dark mode target */
        .dark .target-matched, .body--dark .target-matched { color: #34D399 !important; }
        .dark .target-empty, .body--dark .target-empty { color: #6B7280 !important; }
        
        /* Use balham-dark theme in dark mode */
        .dark .ag-theme-balham,
        .body--dark .ag-theme-balham {
            --ag-background-color: #1e293b;
            --ag-foreground-color: #e2e8f0;
            --ag-header-background-color: #334155;
            --ag-header-foreground-color: #f1f5f9;
            --ag-odd-row-background-color: #1e293b;
            --ag-row-hover-color: #334155;
            --ag-selected-row-background-color: #475569;
            --ag-range-selection-background-color: rgba(71, 85, 105, 0.4);
        }
    """)
    
    return grid, row_data


def create_grid_toolbar(
    row_data: list[dict],
    on_accept_all: Callable[[], None],
    on_reject_all: Callable[[], None],
    on_reset_all: Callable[[], None],
    on_export_csv: Callable[[], None],
) -> None:
    """Create the toolbar above the grid with bulk actions.
    
    Args:
        row_data: Current row data for counting
        on_accept_all: Callback for Accept All button
        on_reject_all: Callback for Reject All button
        on_reset_all: Callback for Reset All button
        on_export_csv: Callback for Export CSV button
    """
    # Count stats
    pending = sum(1 for r in row_data if r.get("status") == "pending" and r.get("action") == "match")
    confirmed = sum(1 for r in row_data if r.get("status") == "confirmed")
    create_new = sum(1 for r in row_data if r.get("action") == "create_new")
    skipped = sum(1 for r in row_data if r.get("action") == "skip")
    clones = sum(1 for r in row_data if r.get("clone_configured"))
    
    with ui.row().classes("w-full items-center justify-between mb-3 flex-wrap gap-2"):
        # Stats
        with ui.row().classes("items-center gap-4"):
            with ui.row().classes("items-center gap-1"):
                ui.badge(str(pending), color="amber").props("dense")
                ui.label("Pending").classes("text-sm")
            
            with ui.row().classes("items-center gap-1"):
                ui.badge(str(confirmed), color="green").props("dense")
                ui.label("Confirmed").classes("text-sm")
            
            with ui.row().classes("items-center gap-1"):
                ui.badge(str(create_new), color="orange").props("dense")
                ui.label("Create New").classes("text-sm")
            
            with ui.row().classes("items-center gap-1"):
                ui.badge(str(skipped), color="grey").props("dense")
                ui.label("Skip").classes("text-sm")
            
            if clones > 0:
                with ui.row().classes("items-center gap-1"):
                    ui.badge(str(clones), color="amber").props("dense")
                    ui.label("Clones").classes("text-sm")
        
        # Actions - use flat buttons with explicit colors for dark mode visibility
        with ui.row().classes("items-center gap-2"):
            ui.button(
                f"Accept All ({pending})",
                icon="check",
                on_click=on_accept_all,
            ).props("size=sm flat text-color=green-6").set_enabled(pending > 0)
            
            ui.button(
                "Reject All",
                icon="close",
                on_click=on_reject_all,
            ).props("size=sm flat text-color=red-6").set_enabled(pending > 0)
            
            ui.button(
                "Reset",
                icon="refresh",
                on_click=on_reset_all,
            ).props("size=sm flat")
            
            ui.button(
                "Export CSV",
                icon="download",
                on_click=on_export_csv,
            ).props("size=sm flat")


def export_mappings_to_csv(row_data: list[dict]) -> str:
    """Export mapping data to CSV format.
    
    Args:
        row_data: Grid row data
        
    Returns:
        CSV string
    """
    lines = ["source_key,source_name,source_type,action,target_id,target_name,status,clone_configured,clone_name"]
    
    for row in row_data:
        line = ",".join([
            f'"{row.get("source_key", "")}"',
            f'"{row.get("source_name", "")}"',
            f'"{row.get("source_type", "")}"',
            f'"{row.get("action", "")}"',
            f'"{row.get("target_id", "")}"',
            f'"{row.get("target_name", "")}"',
            f'"{row.get("status", "")}"',
            f'"{row.get("clone_configured", False)}"',
            f'"{row.get("clone_name", "")}"',
        ])
        lines.append(line)
    
    return "\n".join(lines)
