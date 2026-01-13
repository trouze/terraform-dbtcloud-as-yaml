# Release Notes - v0.7.3

**Release Date:** 2026-01-13  
**Type:** Patch Release  
**Focus:** Web UI Entity Table Bug Fixes

---

## Summary

This patch release fixes critical bugs in the Web UI's Explore Entities tab, specifically around column visibility and duplicate column name issues in the AG Grid table.

---

## Changes

### Fixed

#### Column Visibility Selector Not Working
- **Issue:** Changing column visibility in the column selector dialog had no effect on the displayed table
- **Root Cause:** NiceGUI's `grid.options["columnDefs"]` + `grid.update()` method doesn't properly trigger AG Grid column re-reads
- **Fix:** Now using AG Grid's `setGridOption("columnDefs", ...)` API via `run_grid_method()` for reliable column updates

#### Duplicate Column Names ("Sort Key 2", "Name 3", "Project 1")
- **Issue:** Column headers displayed with numbers appended (e.g., "Name 3", "Project 1")
- **Root Cause:** AG Grid's sorting-related properties (`initialState.sortModel`, column-level `sort` and `sortIndex`) were creating phantom/duplicate column references when used with NiceGUI's AGGrid component
- **Fix:** Removed all sorting-related properties from column definitions
- **Trade-off:** Table no longer has default sorting; users can click column headers to sort manually

### Added

#### "Default" Button in Column Selector
- New button resets column visibility to optimized defaults for the currently selected entity type
- Each entity type (Jobs, Environments, Projects, etc.) has curated default columns showing the most useful fields

#### Explicit Column IDs
- Added `colId` property to all column definitions to prevent AG Grid auto-numbering

### Changed

#### Column Header Clarity
- Changed line number column header from "#" to "Line #" for better clarity

---

## Technical Details

### AG Grid Integration Notes

When using NiceGUI's `ui.aggrid` component:

1. **Column Updates:** Use `await grid.run_grid_method("setGridOption", "columnDefs", new_defs)` instead of modifying `grid.options` directly
2. **Avoid Sorting Properties:** Do not use `initialState.sortModel`, column-level `sort`, or `sortIndex` properties - these create phantom columns in NiceGUI's implementation
3. **Use Explicit `colId`:** Always set `colId` on columns to prevent AG Grid's automatic ID generation

### Files Changed

- `importer/web/components/entity_table.py` - Column visibility, sorting, and default button logic
- `importer/VERSION` - Version bump
- `CHANGELOG.md` - Release notes
- `dev_support/importer_implementation_status.md` - Status update
- `dev_support/phase5_e2e_testing_guide.md` - Version reference

---

## Upgrade Notes

No breaking changes. Direct upgrade from v0.7.2 is supported.

---

## Known Limitations

- Default sorting is no longer applied automatically due to AG Grid/NiceGUI compatibility issues
- Users must click column headers to sort the table
