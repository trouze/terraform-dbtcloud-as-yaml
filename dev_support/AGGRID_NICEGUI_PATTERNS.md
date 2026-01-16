# AG Grid Community Edition + NiceGUI Patterns

> **Purpose:** This document captures hard-won patterns and solutions discovered while building production data grid interfaces with AG Grid Community Edition in NiceGUI. It serves as both human-readable documentation and a structured reference for AI agents working with this stack.

---

## Quick Reference: Critical Rules for AI Agents

When working with AG Grid in NiceGUI, follow these rules:

### MUST DO
1. **Always set explicit `colId`** on every column definition
2. **Use `run_grid_method("setGridOption", ...)`** for runtime column updates
3. **Use `quartz` theme** for automatic dark mode support
4. **Convert Observable types to plain dicts** before passing to grid: `[dict(j) for j in data]`
5. **Use `stopEditingWhenCellsLoseFocus: True`** when cells are editable
6. **Use CSS Grid layout** with `grid-template-rows: auto 1fr` for proper sizing
7. **Use `:valueFormatter`** (colon prefix) for JavaScript function strings
8. **Use `cellClassRules`** instead of `cellRenderer` for conditional styling
9. **For dialogs:** Use `with ui.dialog() as dialog, ui.card()` pattern, call `dialog.open()` after
10. **Always include a close button** in dialogs: `ui.button(icon="close", on_click=dialog.close).props("flat round dense")`
11. **Use AG Grid v32+ row selection API:** `rowSelection.checkboxes` and `rowSelection.headerCheckbox`
12. **Add `cellDataType: False`** to boolean columns to prevent unwanted checkbox rendering
13. **Update this document** when you discover new nuances or patterns

### MUST NOT DO
1. **Never use `initialState.sortModel`** - creates phantom columns
2. **Never use column-level `sort` or `sortIndex`** properties - same issue
3. **Never use `getRowId`** - causes issues with NiceGUI's AG Grid wrapper
4. **Never mutate `grid.options["columnDefs"]` directly** - won't trigger updates
5. **Never assume `grid.update()` will refresh column definitions** - it won't
6. **Never use deprecated `headerCheckboxSelection` or `checkboxSelection`** on columns - use `rowSelection` options instead (AG Grid v32.2+)

---

## 1. Column Definition Nuances

### 1.1 The Phantom Column Bug

**Problem:** Column headers display with numbers appended, like "Name 3", "Sort Key 2", "Project 1".

**Root Cause:** AG Grid's sorting-related properties interact poorly with NiceGUI's wrapper, creating duplicate/phantom column references.

**Problematic Properties:**
```python
# DON'T use any of these:
{
    "initialState": {
        "sortModel": [{"colId": "name", "sort": "asc"}]  # BROKEN
    }
}

# DON'T use column-level sort properties:
{
    "field": "name",
    "sort": "asc",       # BROKEN
    "sortIndex": 0,      # BROKEN
}
```

**Solution:**
1. Remove ALL sorting-related properties from grid options and column definitions
2. Add explicit `colId` to every column definition
3. Let users sort manually by clicking column headers

```python
# DO this instead:
column_defs = [
    {
        "field": "name",
        "colId": "name",  # REQUIRED: explicit colId prevents auto-numbering
        "headerName": "Name",
        "sortable": True,  # Users can still sort by clicking
    },
    {
        "field": "project_name",
        "colId": "project_name",  # Every column needs this
        "headerName": "Project",
        "sortable": True,
    },
]
```

**Trade-off:** Tables no longer have default sorting on load. This is acceptable because users can click any column header to sort.

### 1.2 Runtime Column Updates

**Problem:** Changing column visibility or definitions at runtime doesn't work with direct options mutation.

```python
# DON'T do this - changes won't appear:
grid.options["columnDefs"] = new_col_defs
grid.update()
```

**Solution:** Use AG Grid's `setGridOption` API via `run_grid_method`:

```python
# DO this instead:
async def update_columns(grid, new_col_defs):
    try:
        await grid.run_grid_method("setGridOption", "columnDefs", new_col_defs)
    except Exception:
        # Fallback for older versions
        grid.options["columnDefs"] = new_col_defs
        grid.update()
```

### 1.3 Complete Column Definition Example

```python
def build_column_defs(visible_cols: list[str]) -> list[dict]:
    """Build AG Grid column definitions with all required properties."""
    
    COLUMN_WIDTHS = {
        "name": 280,
        "project_name": 200,
        "id": 80,
        "type": 110,
    }
    DEFAULT_WIDTH = 140
    
    column_defs = [
        {
            "field": "id",
            "colId": "id",  # Always set explicit colId
            "headerName": "ID",
            "width": COLUMN_WIDTHS["id"],
            "filter": "agNumberColumnFilter",
            "sortable": True,
            "hide": "id" not in visible_cols,
            "pinned": "left",  # Optional: pin important columns
        },
        {
            "field": "name",
            "colId": "name",
            "headerName": "Name",
            "width": COLUMN_WIDTHS["name"],
            "filter": "agTextColumnFilter",
            "sortable": True,
            "hide": "name" not in visible_cols,
            "wrapText": True,      # Enable for long content
            "autoHeight": True,    # Auto-adjust row height
        },
        {
            "field": "project_name",
            "colId": "project_name",
            "headerName": "Project",
            "width": COLUMN_WIDTHS["project_name"],
            "filter": "agTextColumnFilter",
            "sortable": True,
            "hide": "project_name" not in visible_cols,
        },
    ]
    
    return column_defs
```

---

## 2. Layout and Container Patterns

### 2.1 CSS Grid for Proper Sizing

AG Grid needs explicit height to render correctly. Use CSS Grid layout for flexible, responsive sizing.

**Problem:** Grid appears with zero height or doesn't fill available space.

**Solution:** Wrap grid in a CSS Grid container with explicit row sizing:

```python
# Main container with CSS Grid layout
with ui.element("div").style(
    "display: grid; "
    "grid-template-rows: auto 1fr; "  # Toolbar auto, grid fills rest
    "width: 100%; "
    "height: 100%; "
    "gap: 8px; "
    "overflow: hidden;"
):
    # Toolbar row (auto height)
    with ui.row().classes("w-full items-center gap-2"):
        ui.select(...)  # Filter controls
        ui.input(...)   # Search box
    
    # Grid container (fills remaining space)
    grid_container = ui.element("div").classes("w-full h-full").style(
        "min-height: 200px;"  # Minimum for small viewports
    )
    
    with grid_container:
        grid = ui.aggrid({...}, theme="quartz").classes("w-full h-full")
```

### 2.2 Grid Container Rebuild Pattern

When columns change significantly (e.g., type-specific columns), rebuild the entire grid:

```python
grid_container = ui.element("div").classes("w-full h-full").style("min-height: 200px;")
grid_ref = {"grid": None}

def build_grid_in_container():
    """Build the AG Grid inside the container."""
    column_defs = build_column_defs(current_visible_columns)
    row_data = get_filtered_data()
    
    grid = ui.aggrid({
        "columnDefs": column_defs,
        "rowData": row_data,
        "pagination": True,
        "paginationPageSize": 50,
        # ... other options
    }, theme="quartz").classes("w-full h-full")
    
    grid_ref["grid"] = grid
    grid.on("cellClicked", handle_cell_click)

def rebuild_grid():
    """Clear and rebuild the grid with current settings."""
    grid_container.clear()
    with grid_container:
        build_grid_in_container()

# Initial grid creation
with grid_container:
    build_grid_in_container()
```

### 2.3 Height Patterns

```python
# For grids that should fill available space:
grid = ui.aggrid({...}).classes("w-full h-full").style("overflow-x: auto;")

# For grids with fixed height:
grid = ui.aggrid({...}).classes("w-full").style("height: 400px;")

# For auto-height based on content (use sparingly - performance impact):
grid = ui.aggrid({
    "domLayout": "autoHeight",
    ...
}).classes("w-full")

# With flex-grow in a flex container:
grid = ui.aggrid({...}).classes("w-full flex-grow").style(
    "height: 100%; min-height: 300px;"
)
```

---

## 3. Theme and Dark Mode

### 3.1 Theme Selection

AG Grid Community includes several themes. For NiceGUI apps with dark mode:

| Theme | Dark Mode Support | Recommendation |
|-------|------------------|----------------|
| `quartz` | Automatic | **Recommended default** |
| `balham` | Manual CSS required | Use when you need custom styling |
| `alpine` | Manual CSS required | Alternative to balham |

```python
# Recommended: quartz theme for automatic dark mode
grid = ui.aggrid({...}, theme="quartz")

# Alternative: balham with manual dark mode CSS
grid = ui.aggrid({...}, theme="balham")
```

### 3.2 Dark Mode CSS for Balham Theme

When using `balham` theme, add CSS overrides for dark mode:

```python
# Add this CSS when using balham theme
ui.add_css("""
    /* Dark mode overrides for balham theme */
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
```

### 3.3 Custom Cell Styling with Dark Mode

Define both light and dark mode variants for custom cell styles:

```python
ui.add_css("""
    /* Row background colors based on status */
    .row-confirmed {
        background-color: rgba(16, 185, 129, 0.15) !important;
    }
    .row-error {
        background-color: rgba(239, 68, 68, 0.15) !important;
    }
    
    /* Status column colors - light mode */
    .status-pending { color: #D97706 !important; }
    .status-confirmed { color: #059669 !important; font-weight: 600; }
    .status-error { color: #DC2626 !important; font-weight: 600; }
    
    /* Dark mode overrides - brighter colors for visibility */
    .dark .row-confirmed,
    .body--dark .row-confirmed {
        background-color: rgba(16, 185, 129, 0.25) !important;
    }
    .dark .row-error,
    .body--dark .row-error {
        background-color: rgba(239, 68, 68, 0.25) !important;
    }
    
    .dark .status-pending, .body--dark .status-pending { color: #FCD34D !important; }
    .dark .status-confirmed, .body--dark .status-confirmed { color: #6EE7B7 !important; }
    .dark .status-error, .body--dark .status-error { color: #FCA5A5 !important; }
""")
```

---

## 4. Event Handling Patterns

### 4.1 Programmatic Update Flag Pattern

**Problem:** Circular event loops when updating grid data programmatically. For example, selecting a row triggers `selectionChanged`, which updates state, which triggers another selection update.

**Solution:** Use a flag dictionary to skip event handlers during programmatic updates:

```python
# Flag to prevent circular updates
programmatic_update = {"active": False}

def on_cell_value_changed(e):
    """Handle when a cell value changes."""
    # Skip if this is a programmatic update
    if programmatic_update.get("active", False):
        return
    
    # Process the user-initiated change
    if e.args and e.args.get("colId") == "_selected":
        row_data = e.args.get("data", {})
        handle_selection_change(row_data)

grid.on("cellValueChanged", on_cell_value_changed)

async def select_all_programmatically():
    """Select all rows without triggering event handlers."""
    programmatic_update["active"] = True
    try:
        # Update row data
        for row in grid.options.get("rowData", []):
            row["_selected"] = True
        grid.update()
    finally:
        programmatic_update["active"] = False
```

### 4.2 Checkbox Column Pattern

For editable checkbox columns:

```python
column_defs = [
    {
        "field": "_selected",
        "colId": "_selected",
        "headerName": "✓",
        "width": 50,
        "pinned": "left",
        "cellRenderer": "agCheckboxCellRenderer",  # Built-in checkbox
        "editable": True,  # Required for clicking to work
        "cellStyle": {"textAlign": "center"},
    },
    # ... other columns
]

grid = ui.aggrid({
    "columnDefs": column_defs,
    "rowData": row_data,
    "stopEditingWhenCellsLoseFocus": True,  # Important for checkboxes
    # ... other options
}, theme="quartz")

def on_cell_value_changed(e):
    """Handle checkbox toggle."""
    if e.args and e.args.get("colId") == "_selected":
        row_data = e.args.get("data", {})
        new_value = e.args.get("newValue", False)
        handle_selection(row_data, new_value)

grid.on("cellValueChanged", on_cell_value_changed)
```

### 4.3 Cell Click vs Cell Value Changed

Use the right event for your use case:

```python
# For clicking anywhere in a row (read-only interaction)
def on_cell_clicked(e):
    if e.args and "data" in e.args:
        row_data = e.args["data"]
        show_detail_dialog(row_data)

grid.on("cellClicked", on_cell_clicked)

# For editable cells (value changes)
def on_cell_value_changed(e):
    data = e.args.get("data", {})
    col = e.args.get("colId")
    new_val = e.args.get("newValue")
    handle_edit(data, col, new_val)

grid.on("cellValueChanged", on_cell_value_changed)

# For row selection (built-in checkboxes)
async def handle_selection():
    selected = await grid.get_selected_rows()
    process_selection(selected)

grid.on("selectionChanged", lambda: handle_selection())
```

---

## 5. Data Compatibility

### 5.1 Observable Types Conversion

**Problem:** NiceGUI's Observable types (used for reactive state) can cause issues when passed to AG Grid.

**Solution:** Convert to plain Python dicts before passing to grid:

```python
# DON'T pass Observable types directly:
grid = ui.aggrid({
    "rowData": state.items,  # May be Observable
})

# DO convert to plain dicts:
row_data = [dict(item) for item in state.items]
grid = ui.aggrid({
    "rowData": row_data,
})
```

### 5.2 Handling None Values

AG Grid handles None/null differently than Python might expect:

```python
# Handle potential None values before grid
def prepare_row_data(items: list[dict]) -> list[dict]:
    rows = []
    for item in items:
        # Ensure nested objects exist
        project = item.get("project") or {}
        environment = item.get("environment") or {}
        
        rows.append({
            "id": item.get("id"),
            "name": item.get("name", ""),
            "project_name": project.get("name") or f"Project {item.get('project_id', 'N/A')}",
            "env_name": environment.get("name") or f"Env {item.get('environment_id', 'N/A')}",
        })
    return rows
```

---

## 6. Styling Patterns

### 6.1 valueFormatter for Display Text

Use `:valueFormatter` (with colon prefix) for JavaScript function strings:

```python
{
    "field": "action",
    "headerName": "Action",
    # Note the colon prefix for JS functions
    ":valueFormatter": """params => {
        const labels = {
            'match': '⛓️ Match',
            'create_new': '➕ Create New',
            'skip': '⏭️ Skip',
        };
        return labels[params.value] || params.value;
    }""",
}
```

### 6.2 cellClassRules for Conditional Styling

**Prefer `cellClassRules` over `cellRenderer`** for conditional styling - better NiceGUI compatibility:

```python
{
    "field": "status",
    "headerName": "Status",
    ":valueFormatter": """params => {
        const labels = {
            'pending': '⏳ Pending',
            'confirmed': '✓ Confirmed',
            'error': '✗ Error',
        };
        return labels[params.value] || params.value;
    }""",
    "cellClassRules": {
        "status-pending": "x === 'pending'",
        "status-confirmed": "x === 'confirmed'",
        "status-error": "x === 'error'",
    },
}
```

Then define the CSS classes:
```python
ui.add_css("""
    .status-pending { color: #D97706 !important; }
    .status-confirmed { color: #059669 !important; font-weight: 600; }
    .status-error { color: #DC2626 !important; font-weight: 600; }
""")
```

### 6.3 Row Class Rules

Apply classes to entire rows based on data:

```python
grid_options = {
    "columnDefs": column_defs,
    "rowData": row_data,
    "rowClassRules": {
        "row-confirmed": "data.status === 'confirmed'",
        "row-error": "data.status === 'error'",
        "row-skipped": "data.status === 'skipped' || data.action === 'skip'",
    },
}
```

### 6.4 Cell Style for Simple Formatting

For simple, non-conditional styles:

```python
{
    "field": "identifier",
    "headerName": "Identifier",
    "cellStyle": {"fontFamily": "monospace", "fontSize": "12px"},
}
```

---

## 7. Row Selection Patterns

### 7.1 Modern Row Selection Format

Use the object format for row selection (recommended):

```python
# Single row selection
grid = ui.aggrid({
    "rowSelection": {"mode": "singleRow"},
    ...
})

# Multiple row selection
grid = ui.aggrid({
    "rowSelection": {"mode": "multiRow"},
    ...
})
```

### 7.2 Built-in Checkbox Selection (AG Grid v32+)

**⚠️ Deprecation Notice:** As of AG Grid v32.2, `headerCheckboxSelection` and `checkboxSelection` on columns are deprecated. Use `rowSelection` options instead.

```python
# DON'T use the old column-level API (deprecated):
columns = [
    {
        "headerCheckboxSelection": True,  # DEPRECATED
        "checkboxSelection": True,        # DEPRECATED
        "width": 50,
        "pinned": "left",
    },
]

# DO use the new rowSelection API:
grid = ui.aggrid({
    "columnDefs": columns,  # No checkbox column needed!
    "rowSelection": {
        "mode": "multiRow",
        "headerCheckbox": True,    # Replaces headerCheckboxSelection
        "checkboxes": True,        # Replaces checkboxSelection
    },
    "suppressRowClickSelection": True,  # Only checkbox selects, not row click
}, theme="quartz")

# Handle selection changes
async def handle_selection():
    selected = await grid.get_selected_rows()
    selected_ids = [row["id"] for row in selected]
    process_selection(selected_ids)

grid.on("selectionChanged", lambda: handle_selection())
```

### 7.3 Pre-selecting Rows on Grid Load

**Problem:** When restoring selection state from saved data, the grid checkboxes don't show as checked even though your state says they're selected.

**Solution:** Use AG Grid's API to programmatically select rows after the grid renders:

```python
# Pre-selected job IDs based on saved state
pre_selected_ids = set(state.selected_ids)
all_selected = pre_selected_ids and len(pre_selected_ids) == len(rows)

grid = ui.aggrid({
    "columnDefs": columns,
    "rowData": rows,
    "rowSelection": {
        "mode": "multiRow",
        "headerCheckbox": True,
        "checkboxes": True,
    },
}, theme="quartz")

# Pre-select rows based on saved state
if all_selected:
    # If all rows are selected, use selectAll() for simplicity
    async def select_all_rows():
        await grid.run_grid_method("selectAll")
    ui.timer(0.1, select_all_rows, once=True)
elif pre_selected_ids:
    # For partial selection, use JavaScript to select by IDs
    ids_list = list(pre_selected_ids)
    js_code = f"""
        const selectedIds = {ids_list};
        getElement({grid.id}).gridOptions.api.forEachNode(node => {{
            if (selectedIds.includes(node.data.id)) {{
                node.setSelected(true);
            }}
        }});
    """
    ui.timer(0.2, lambda: ui.run_javascript(js_code), once=True)
```

**Key Points:**
- Use `ui.timer` with a small delay to ensure the grid is fully rendered
- `selectAll()` is simpler and more reliable for selecting all rows
- For partial selection, use JavaScript `forEachNode` to select specific rows by ID

### 7.4 Preventing Boolean Fields from Rendering as Checkboxes

**Problem:** Boolean fields (like `is_managed`) automatically render as checkboxes in AG Grid, creating confusing duplicate checkboxes in your grid.

**Solution:** Add `cellDataType: False` to prevent automatic checkbox rendering:

```python
# DON'T let boolean fields auto-render as checkboxes:
{
    "field": "is_managed",
    "headerName": "Managed",
    # Without cellDataType, this renders as a checkbox!
}

# DO explicitly disable the boolean cell type:
{
    "field": "is_managed",
    "colId": "is_managed",
    "headerName": "Managed",
    "cellDataType": False,  # Prevents checkbox rendering
    ":valueFormatter": "params => params.value ? '✓ Yes' : ''",
    "cellClassRules": {
        "text-green-600": "x === true",
    },
}
```

Then add the CSS class:
```python
ui.add_css("""
    .text-green-600 { color: #059669 !important; font-weight: 600; }
    .dark .text-green-600, .body--dark .text-green-600 { color: #6EE7B7 !important; }
""")
```

---

## 8. Known Limitations

### 8.1 No Default Sorting

Due to the phantom column bug, default sorting on page load is not supported. Users must click column headers to sort.

**Workaround:** Pre-sort your data in Python before passing to the grid:

```python
# Sort data before passing to grid
sorted_data = sorted(row_data, key=lambda x: x.get("name", ""))
grid = ui.aggrid({
    "rowData": sorted_data,
    ...
})
```

### 8.2 getRowId Not Supported

The `getRowId` option causes issues with NiceGUI's AG Grid wrapper. Don't use it:

```python
# DON'T do this:
grid_options = {
    "getRowId": "params => params.data.id",  # BROKEN
}

# DO rely on default row ID behavior or use row index
```

### 8.3 Animation Stability

`animateRows` can cause visual glitches in some scenarios:

```python
# For maximum stability, disable animations:
grid = ui.aggrid({
    "animateRows": False,
    ...
})

# Enable only if needed and tested:
grid = ui.aggrid({
    "animateRows": True,
    ...
})
```

---

## 9. Complete Working Example

Here's a complete example incorporating all patterns (AG Grid v32+):

```python
from nicegui import ui

def create_data_grid(items: list[dict], on_selection_change: callable, pre_selected_ids: set = None) -> ui.aggrid:
    """Create a properly configured AG Grid with all best practices."""
    
    # Convert Observable types to plain dicts
    row_data = [dict(item) for item in items]
    pre_selected_ids = pre_selected_ids or set()
    
    # Prepare row data with safe null handling
    for row in row_data:
        if row.get("project") is None:
            row["project_name"] = "N/A"
        else:
            row["project_name"] = row["project"].get("name", "N/A")
    
    # Column definitions with explicit colId
    # NOTE: No checkbox column needed - AG Grid v32+ adds it via rowSelection options
    column_defs = [
        {
            "field": "name",
            "colId": "name",
            "headerName": "Name",
            "width": 200,
            "filter": "agTextColumnFilter",
            "sortable": True,
        },
        {
            "field": "status",
            "colId": "status",
            "headerName": "Status",
            "width": 120,
            ":valueFormatter": """params => {
                const labels = {
                    'active': '✓ Active',
                    'pending': '⏳ Pending',
                    'error': '✗ Error',
                };
                return labels[params.value] || params.value;
            }""",
            "cellClassRules": {
                "status-active": "x === 'active'",
                "status-pending": "x === 'pending'",
                "status-error": "x === 'error'",
            },
        },
        {
            "field": "is_active",
            "colId": "is_active",
            "headerName": "Active",
            "width": 80,
            "cellDataType": False,  # IMPORTANT: Prevents boolean → checkbox
            ":valueFormatter": "params => params.value ? '✓' : ''",
        },
        {
            "field": "project_name",
            "colId": "project_name",
            "headerName": "Project",
            "width": 180,
            "filter": "agTextColumnFilter",
            "sortable": True,
        },
    ]
    
    # Grid options - NO sorting properties, NO getRowId
    # Using AG Grid v32+ rowSelection API
    grid_options = {
        "columnDefs": column_defs,
        "rowData": row_data,
        "rowSelection": {
            "mode": "multiRow",
            "headerCheckbox": True,  # Replaces headerCheckboxSelection
            "checkboxes": True,      # Replaces checkboxSelection
        },
        "suppressRowClickSelection": True,  # Only checkbox selects
        "pagination": True,
        "paginationPageSize": 50,
        "paginationPageSizeSelector": [25, 50, 100],
        "headerHeight": 36,
        "rowClassRules": {
            "row-active": "data.status === 'active'",
            "row-error": "data.status === 'error'",
        },
        "defaultColDef": {
            "resizable": True,
            "sortable": True,
            "filter": True,
            "minWidth": 80,
        },
        "stopEditingWhenCellsLoseFocus": True,
        "animateRows": False,  # Stability
    }
    
    # Create grid with quartz theme for dark mode support
    grid = ui.aggrid(grid_options, theme="quartz").classes("w-full h-full")
    
    # Pre-select rows based on saved state (AG Grid v32+ pattern)
    all_selected = pre_selected_ids and len(pre_selected_ids) == len(row_data)
    if all_selected:
        async def select_all_rows():
            await grid.run_grid_method("selectAll")
        ui.timer(0.1, select_all_rows, once=True)
    elif pre_selected_ids:
        ids_list = list(pre_selected_ids)
        js_code = f"""
            const selectedIds = {ids_list};
            getElement({grid.id}).gridOptions.api.forEachNode(node => {{
                if (selectedIds.includes(node.data.id)) {{
                    node.setSelected(true);
                }}
            }});
        """
        ui.timer(0.2, lambda: ui.run_javascript(js_code), once=True)
    
    # Handle selection changes (AG Grid v32+ pattern)
    async def handle_selection():
        selected = await grid.get_selected_rows()
        selected_ids = [row["id"] for row in selected]
        on_selection_change(selected_ids)
    
    grid.on("selectionChanged", lambda: handle_selection())
    
    # Add custom CSS with dark mode support
    ui.add_css("""
        .status-active { color: #059669 !important; font-weight: 600; }
        .status-pending { color: #D97706 !important; }
        .status-error { color: #DC2626 !important; font-weight: 600; }
        
        .row-active { background-color: rgba(16, 185, 129, 0.1) !important; }
        .row-error { background-color: rgba(239, 68, 68, 0.1) !important; }
        
        .dark .status-active, .body--dark .status-active { color: #6EE7B7 !important; }
        .dark .status-pending, .body--dark .status-pending { color: #FCD34D !important; }
        .dark .status-error, .body--dark .status-error { color: #FCA5A5 !important; }
        
        .dark .row-active, .body--dark .row-active {
            background-color: rgba(16, 185, 129, 0.2) !important;
        }
        .dark .row-error, .body--dark .row-error {
            background-color: rgba(239, 68, 68, 0.2) !important;
        }
    """)
    
    return grid


# Usage in a page
def create_page():
    with ui.element("div").style(
        "display: grid; "
        "grid-template-rows: auto 1fr; "
        "height: 100%; "
        "gap: 8px; "
        "overflow: hidden;"
    ):
        # Toolbar
        with ui.row().classes("w-full items-center gap-2"):
            ui.input(placeholder="Search...").props("outlined dense")
            ui.button("Refresh", icon="refresh")
        
        # Grid container
        with ui.element("div").classes("w-full h-full").style("min-height: 200px;"):
            grid = create_data_grid(
                items=my_data,
                on_selection_change=handle_selection,
            )
```

---

## 10. Dialog and Popup Patterns

When using AG Grid, you often need dialogs for detail views, configuration, or data entry. Here are the established patterns.

### 10.1 Basic Dialog Pattern

Use the `with ui.dialog() as dialog, ui.card()` pattern for clean dialog creation:

```python
def show_detail_dialog(row_data: dict) -> None:
    """Show a dialog with row details."""
    
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-4xl").style("height: 80vh;"):
        # Header with close button
        with ui.row().classes("w-full items-center justify-between p-4 border-b"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("info")
                ui.label(row_data.get("name", "Details")).classes("text-xl font-bold")
            # Close button - always include this
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")
        
        # Content area with scroll
        with ui.scroll_area().style("height: 60vh;"):
            # Your content here
            ui.json_editor(row_data)
    
    # IMPORTANT: Call open() after defining the dialog
    dialog.open()
```

### 10.2 Dialog Triggered from Grid Cell Click

```python
def on_cell_clicked(e):
    """Handle cell click to show entity details."""
    # Skip for checkbox column clicks
    if e.args and e.args.get("colId") == "_selected":
        return
    
    if e.args and "data" in e.args:
        row_data = e.args["data"]
        show_detail_dialog(row_data)

grid.on("cellClicked", on_cell_clicked)
```

### 10.3 Configuration Dialog with Actions

For dialogs with apply/cancel actions (like column selector):

```python
def show_config_dialog():
    """Show a configuration dialog with apply/cancel."""
    
    with ui.dialog() as dialog, ui.card().classes("p-4 min-w-[400px] max-h-[80vh]"):
        ui.label("Configuration").classes("text-lg font-semibold mb-2")
        
        # Scrollable content area
        with ui.scroll_area().style("max-height: 400px;"):
            # Configuration controls
            checkbox1 = ui.checkbox("Option 1", value=True)
            checkbox2 = ui.checkbox("Option 2", value=False)
        
        # Action buttons - always at bottom
        with ui.row().classes("w-full justify-end mt-4 gap-2"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            
            async def apply_config():
                # Apply changes
                save_configuration(checkbox1.value, checkbox2.value)
                dialog.close()
                ui.notify("Configuration saved", type="positive")
            
            ui.button("Apply", on_click=apply_config).props("color=primary")
    
    dialog.open()
```

### 10.4 Maximized Viewer Dialog

For full-screen viewers (YAML, JSON, logs):

```python
def create_viewer_dialog(content: str, title: str) -> ui.dialog:
    """Create a maximized viewer dialog."""
    
    with ui.dialog() as dialog:
        # Maximized mode - fills the screen
        dialog.props("maximized")
        
        with ui.card().classes("w-full h-full").style("display: flex; flex-direction: column;"):
            # Header
            with ui.row().classes("w-full items-center justify-between p-4"):
                ui.label(title).classes("text-xl font-bold")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense")
            
            # Content fills remaining space
            with ui.scroll_area().classes("w-full").style("flex: 1; min-height: 0;"):
                ui.code(content, language="json").classes("w-full text-sm")
    
    return dialog

# Usage
dialog = create_viewer_dialog(json_content, "Entity Details")
dialog.open()
```

### 10.5 Dialog with Tabs

For complex detail views with multiple sections:

```python
def show_tabbed_detail_dialog(row_data: dict, full_data: dict) -> None:
    """Show a dialog with tabbed content."""
    
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-6xl").style("height: 80vh;"):
        # Header
        with ui.row().classes("w-full items-center justify-between p-4 border-b"):
            ui.label(row_data.get("name", "Details")).classes("text-xl font-bold")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")
        
        # Tabs
        with ui.tabs().classes("w-full") as tabs:
            summary_tab = ui.tab("Summary", icon="summarize")
            details_tab = ui.tab("Details", icon="table_rows")
            json_tab = ui.tab("JSON", icon="code")
        
        # Tab panels - flex-1 to fill remaining height
        with ui.tab_panels(tabs, value=summary_tab).classes("w-full flex-1"):
            with ui.tab_panel(summary_tab):
                with ui.scroll_area().style("height: 55vh;"):
                    render_summary(row_data)
            
            with ui.tab_panel(details_tab):
                with ui.scroll_area().style("height: 55vh;"):
                    render_details(full_data)
            
            with ui.tab_panel(json_tab):
                formatted_json = json.dumps(full_data, indent=2)
                with ui.column().classes("w-full gap-2"):
                    # Copy button
                    with ui.row().classes("w-full justify-end"):
                        ui.button(
                            "Copy",
                            icon="content_copy",
                            on_click=lambda: (
                                ui.run_javascript(
                                    f"navigator.clipboard.writeText({json.dumps(formatted_json)})"
                                ),
                                ui.notify("Copied to clipboard", type="positive"),
                            ),
                        ).props("flat dense")
                    
                    with ui.scroll_area().style("height: 55vh;"):
                        ui.code(formatted_json, language="json").classes("w-full text-xs")
    
    dialog.open()
```

### 10.6 Dialog Rules Summary

| Pattern | Use Case |
|---------|----------|
| `ui.card().classes("max-w-4xl").style("height: 80vh;")` | Standard detail dialog |
| `ui.card().classes("p-4 min-w-[400px] max-h-[80vh]")` | Configuration/picker dialog |
| `dialog.props("maximized")` | Full-screen viewer |
| `ui.scroll_area().style("height: 55vh;")` | Scrollable content in tabs |
| `ui.button(icon="close", on_click=dialog.close).props("flat round dense")` | Always include close button |

---

## 11. Troubleshooting Guide

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| Column headers show "Name 3", "Sort Key 2" | Sorting properties causing phantom columns | Remove `initialState.sortModel`, `sort`, `sortIndex`; add explicit `colId` |
| Column visibility changes don't apply | Using `grid.options` mutation | Use `run_grid_method("setGridOption", "columnDefs", ...)` |
| Grid has zero height | No explicit height in container | Use CSS Grid with `grid-template-rows: auto 1fr` |
| Checkbox clicks don't register | Missing `editable: True` | Add `editable: True` to checkbox column |
| Event handler fires multiple times | Circular update loop | Use `programmatic_update` flag pattern |
| Dark mode colors wrong | Missing dark mode CSS | Add `.dark` and `.body--dark` CSS selectors |
| Grid crashes with Observable data | Reactive types not compatible | Convert with `[dict(item) for item in data]` |
| Cell editing doesn't commit | Focus handling issue | Add `stopEditingWhenCellsLoseFocus: True` |
| Dialog doesn't appear | Missing `dialog.open()` | Call `dialog.open()` after defining the dialog |
| Dialog content overflows | No scroll area | Wrap content in `ui.scroll_area().style("height: Xvh;")` |
| Dialog has no close button | Missing close handler | Add `ui.button(icon="close", on_click=dialog.close).props("flat round dense")` |
| Two checkbox columns appear | Boolean field auto-renders as checkbox | Add `cellDataType: False` to boolean columns |
| Selection checkboxes never checked | Selection state not applied to grid | Use `selectAll()` or `forEachNode` with `ui.timer` to pre-select rows |
| Deprecation warnings about checkboxSelection | Using old AG Grid API | Use `rowSelection.checkboxes` and `rowSelection.headerCheckbox` instead |

---

## References

- **Source Files:**
  - `importer/web/components/entity_table.py` - Primary patterns for column handling, detail dialogs
  - `importer/web/components/match_grid.py` - Styling and dark mode patterns
  - `importer/web/pages/scope.py` - Event handling and checkbox patterns
  - `importer/web/workflows/jobs_as_code/pages/jobs.py` - Row selection patterns
  - `importer/web/utils/yaml_viewer.py` - Maximized viewer dialog patterns

- **Release Notes:**
  - `dev_support/RELEASE_NOTES_v0.7.3.md` - Bug fixes and technical details

- **External Docs:**
  - [NiceGUI AGGrid Documentation](https://nicegui.io/documentation/aggrid)
  - [AG Grid Community Docs](https://www.ag-grid.com/javascript-data-grid/)

---

## Contributing to This Document

> **This is a living document.** When you discover new AG Grid + NiceGUI nuances while working on this codebase, **update this document immediately**.

### When to Update

Update this document when you:
- Discover a new bug or incompatibility
- Find a workaround for an AG Grid issue
- Establish a new pattern that should be reused
- Fix an issue that took significant debugging time
- Learn something non-obvious about the NiceGUI/AG Grid interaction

### How to Update

1. **Add to the relevant section** if the pattern fits an existing category
2. **Create a new section** if it's a distinct topic (follow the existing format)
3. **Update the Troubleshooting Guide** with symptom → cause → solution
4. **Update the Quick Reference** if it's a critical rule that AI agents must follow
5. **Add source file references** so others can see working examples

### Update Format

For new issues, use this format:

```markdown
### X.Y Section Title

**Problem:** Clear description of what went wrong or was confusing.

**Root Cause:** Technical explanation of why it happened.

**Solution:** Code example showing the correct approach.

```python
# Example code
```

**Trade-off:** (if applicable) Any downsides to the solution.
```

### For AI Agents

When referencing this document:
- **Read the Quick Reference section first** - it has the critical rules
- **Check the Troubleshooting Guide** if you encounter an issue
- **If you solve a new problem**, add it to this document before completing your task
- **Link to this document** in commit messages when making AG Grid-related changes

### Document History

| Date | Change | Author |
|------|--------|--------|
| 2026-01-16 | Initial document created from codebase analysis | AI Assistant |
| 2026-01-16 | Added AG Grid v32+ row selection API patterns (sections 7.2-7.4), updated Quick Reference with deprecation warnings | AI Assistant |

---

*Last updated: 2026-01-16*
