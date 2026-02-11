---
name: Unadopt Action + Type Filter
overview: Add an "Unadopt" action to the match grid action column (mapping to removal_keys / terraform state rm), and replace the AG Grid column header filter with a single-select type dropdown matching the explore grid pattern.
todos:
  - id: unadopt-action-col
    content: "Add 'unadopt' to match_grid.py action column: cellEditorParams values, valueFormatter, cellClassRules, row class rules"
    status: completed
  - id: unadopt-cell-handler
    content: Add 'unadopt' branch in on_cell_changed handler (match_grid.py) with on_unadopt callback parameter
    status: completed
  - id: unadopt-match-wiring
    content: "Wire unadopt in match.py: on_row_change adds to removal_keys, on_unadopt callback, stat card, create_match_grid call"
    status: completed
  - id: unadopt-toolbar-badge
    content: Add 'Unadopt' badge count to create_grid_toolbar stats
    status: completed
  - id: type-filter-dropdown
    content: Add single-select ui.select type filter dropdown to create_grid_toolbar (same pattern as entity_table.py explore grids)
    status: completed
  - id: type-filter-wiring
    content: "Wire type filter in match.py: callback uses grid.call_api_method('setFilterModel') to filter source_type column"
    status: completed
isProject: false
---

# Add "Unadopt" Action and Type Filter Dropdown to Match Grid

## 1. Add "Unadopt" Action to the Grid

The match grid currently has 4 actions: `match`, `create_new`, `skip`, `adopt`. The backend already supports removal via `DISP_REMOVED` and `removal_keys` in [target_intent.py](importer/web/utils/target_intent.py) (line 30: `DISP_REMOVED = "removed"`), but no UI action exposes it.

### Changes in [match_grid.py](importer/web/components/match_grid.py)

**Action column definition** (lines 1142-1166): Add `"unadopt"` to the `cellEditorParams.values` list, the `valueFormatter` labels map, and `cellClassRules`:

```python
"values": ["match", "create_new", "skip", "adopt", "unadopt"],
# In valueFormatter:
'unadopt': '🔓 Unadopt',
# In cellClassRules:
"action-unadopt": "x === 'unadopt'",
```

`**on_cell_changed` handler** (lines 1298-1331): Add an `elif new_val == "unadopt"` branch:

```python
elif new_val == "unadopt":
    # Unadopt: remove resource from TF management (terraform state rm)
    # Keep target_id for reference but mark as removal candidate
    data["status"] = "unadopted"
    on_row_change(data)
    # Trigger unadopt callback if provided
    if on_unadopt:
        source_key = data.get("source_key", "")
        if source_key:
            on_unadopt(source_key)
```

`**create_match_grid` signature** (line 1028): Add `on_unadopt: Optional[Callable[[str], None]] = None` parameter.

**Toolbar stats** (`create_grid_toolbar`, line 1553): Add an "Unadopt" badge count alongside the existing Pending/Confirmed/Create New/Skip badges.

**Row class rules** (line 1280 area): Add `"row-unadopted": "data.action === 'unadopt'"` for visual styling.

### Changes in [match.py](importer/web/pages/match.py)

`**on_row_change` handler** (line 824): Add `"unadopt"` to the set of actions that removes from `confirmed_mappings`, and add the source_key to `state.map.removal_keys` (or equivalent persistent set):

```python
if action in ("skip", "create_new", "unadopt"):
    state.map.confirmed_mappings = [
        m for m in state.map.confirmed_mappings
        if m.get("source_key") != source_key
    ]
if action == "unadopt":
    # Add to removal keys for target intent
    if not hasattr(state.map, 'removal_keys'):
        state.map.removal_keys = set()
    state.map.removal_keys.add(source_key)
elif action != "unadopt" and hasattr(state.map, 'removal_keys'):
    # Switching away from unadopt - remove from removal keys
    state.map.removal_keys.discard(source_key)
```

**Stat cards** (line 344): Add an "Unadopt" stat card with a count.

`**create_match_grid` call** (line 1272): Pass `on_unadopt=on_unadopt` callback.

### Availability Logic

The "unadopt" action only makes sense for resources that are currently in TF state. Rows without `state_id` should not offer unadopt. This can be enforced in one of two ways:

- **Option A** (simpler): Allow it in the dropdown always; the deploy step ignores unadopt for non-state resources.
- **Option B** (stricter): Use a dynamic `cellEditorParams` based on row data (AG Grid supports `cellEditorParams` as a function). This is more complex with NiceGUI's AG Grid binding.

Recommend **Option A** for now -- it keeps the grid simple and the deploy step already validates.

---

## 2. Replace AG Grid Column Filter with Type Dropdown

Currently, the match grid uses AG Grid's built-in column header filter for the Type column (default `filter: True`). The explore grids use a `ui.select` dropdown above the grid. The user wants the same pattern.

### Changes in [match_grid.py](importer/web/components/match_grid.py)

`**create_grid_toolbar**` (line 1553): Add a `type_filter` parameter and render a `ui.select` dropdown. The toolbar signature becomes:

```python
def create_grid_toolbar(
    row_data: list[dict],
    on_accept_all: Callable[[], None],
    on_reject_all: Callable[[], None],
    on_reset_all: Callable[[], None],
    on_export_csv: Callable[[], None],
    on_type_filter_change: Optional[Callable[[str], None]] = None,
) -> None:
```

Add before the action buttons:

```python
# Type filter dropdown (like explore grids)
types_in_data = sorted(set(r.get("source_type", "UNK") for r in row_data))
type_counts = {}
for r in row_data:
    t = r.get("source_type", "UNK")
    type_counts[t] = type_counts.get(t, 0) + 1

TYPE_LABELS = {
    'ACC': 'Account', 'CON': 'Connection', 'REP': 'Repository',
    'TOK': 'Token', 'GRP': 'Group', 'NOT': 'Notify',
    'WEB': 'Webhook', 'PLE': 'PrivateLink', 'PRJ': 'Project',
    'ENV': 'Environment', 'VAR': 'EnvVar', 'JOB': 'Job',
    'JEVO': 'EnvVar Ovr', 'JCTG': 'Job Trigger', 'PREP': 'Repo Link',
}

filter_options = {"all": f"All Types ({len(row_data)})"}
for t in types_in_data:
    label = TYPE_LABELS.get(t, t)
    filter_options[t] = f"{label} ({t}) [{type_counts.get(t, 0)}]"

ui.select(
    options=filter_options,
    value="all",
    on_change=lambda e: on_type_filter_change(e.value) if on_type_filter_change else None,
).props("outlined dense").classes("min-w-[200px]")
```

### Changes in [match.py](importer/web/pages/match.py)

**Grid filtering**: Add a `current_type_filter` ref and a callback that uses AG Grid's `setFilterModel` API to apply an external filter on the `source_type` column:

```python
current_type_filter = {"type": "all"}

def on_type_filter_change(type_value: str):
    current_type_filter["type"] = type_value
    if type_value == "all":
        # Clear the filter
        grid.call_api_method("setFilterModel", {})
    else:
        # Apply filter on source_type column
        grid.call_api_method("setFilterModel", {
            "source_type": {"filterType": "text", "type": "equals", "filter": type_value}
        })
```

Pass `on_type_filter_change` to `create_grid_toolbar`.

**Note**: The AG Grid `setFilterModel` approach is preferred because it keeps all rows in the grid (preserving user edits to action/target_id) and just hides non-matching rows. A Python-side filter would require regenerating row data.

---

## Key Files


| File                                                    | Change                                                                                       |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [match_grid.py](importer/web/components/match_grid.py)  | Add `unadopt` to action column, add type dropdown to toolbar, add unadopt styling/stats      |
| [match.py](importer/web/pages/match.py)                 | Wire unadopt callback to `removal_keys`, wire type filter to grid API, add unadopt stat card |
| [target_intent.py](importer/web/utils/target_intent.py) | No changes needed -- `removal_keys` and `DISP_REMOVED` already exist                         |


