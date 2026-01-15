# Release Notes v0.8.1

**Release Date:** 2026-01-15  
**Type:** Patch Release  
**Focus:** Deploy Page UI Polish & Terminal Output Improvements

---

## Overview

This patch release focuses on improving the Deploy page user experience with better visual feedback for terraform operations, enhanced terminal output formatting, and proper button state management.

---

## New Features

### Dynamic Output Panel Title
The Output panel now displays which step's logs are being shown:
- `Output — GENERATE` during file generation
- `Output — INIT` during terraform init
- `Output — VALIDATE` during terraform validate
- `Output — PLAN` during terraform plan
- `Output — APPLY` during terraform apply
- `Output — DESTROY` during terraform destroy

### Status Colors for Buttons
Deploy buttons now change color based on operation result:
- **Green** (`#22C55E`): Operation succeeded without warnings
- **Yellow** (`#EAB308`): Operation succeeded with warnings (e.g., "Provider development overrides")
- **Red** (`#EF4444`): Operation failed with errors

### Auto-Detection of Log Levels
Terminal output now automatically detects and displays appropriate log levels:
- Lines containing `Warning:` are displayed with WARN level (yellow badge)
- Lines containing `Error:` are displayed with ERROR level (red badge)
- All other lines remain INFO level

---

## Improvements

### ISO8601 Timestamps with Timezone
Terminal output timestamps now include the timezone offset:
- **Before:** `07:36:21`
- **After:** `2026-01-15T07:36:21-0800`

### Wider Search Bar
The terminal search bar width increased from 150px to 250px for better usability.

### Button State Reset
When regenerating Terraform files, all downstream buttons (Init, Validate, Plan, Apply) now properly reset to their disabled visual state:
- Outline border restored
- Opacity reduced to 50%
- Orange background removed

---

## Bug Fixes

- Fixed buttons retaining enabled appearance when regenerating files
- Fixed button styles not clearing before applying new colors
- Changed "This will create/modify resources" message from WARN to INFO (prevents false yellow button state)

---

## Technical Details

### Files Modified
- `importer/web/components/terminal_output.py` - Added `set_title()`, `info_auto()` methods, ISO8601 timestamps
- `importer/web/pages/deploy.py` - Status colors, dynamic titles, button state management

### New Methods
```python
# terminal_output.py
def set_title(self, title: str) -> None:
    """Update the terminal output title dynamically."""

def info_auto(self, text: str) -> None:
    """Log with auto-detected level based on 'Warning:' or 'Error:' prefixes."""
```

### Status Color Constants
```python
STATUS_SUCCESS = "#22C55E"  # green-500
STATUS_WARNING = "#EAB308"  # yellow-500
STATUS_ERROR = "#EF4444"    # red-500
```

---

## Upgrade Notes

This is a patch release with no breaking changes. Simply update to the new version:

```bash
# Check current version
python3 -c "from importer import get_version; print(get_version())"

# Should output: 0.8.1
```

---

## What's Next

- Additional UI polish based on user feedback
- Performance optimizations for large account migrations
- Enhanced error recovery and retry mechanisms
