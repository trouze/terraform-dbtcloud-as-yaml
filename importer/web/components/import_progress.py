"""Import progress UI component for showing resource import status."""

from typing import Optional

from nicegui import ui

from importer.web.utils.terraform_import import ImportResult, ImportSummary


# Status colors
STATUS_COLORS = {
    "pending": "#6B7280",    # gray-500
    "importing": "#3B82F6",  # blue-500
    "success": "#22C55E",    # green-500
    "failed": "#EF4444",     # red-500
    "skipped": "#F59E0B",    # yellow-500
}

STATUS_ICONS = {
    "pending": "schedule",
    "importing": "sync",
    "success": "check_circle",
    "failed": "error",
    "skipped": "skip_next",
}


# Resource type labels
RESOURCE_TYPE_LABELS = {
    "PRJ": "Project",
    "ENV": "Environment",
    "JOB": "Job",
    "CON": "Connection",
    "REP": "Repository",
    "TOK": "Service Token",
    "GRP": "Group",
    "NOT": "Notification",
    "WEB": "Webhook",
    "VAR": "Env Variable",
}


class ImportProgressTable:
    """Component for displaying import progress with per-resource status."""
    
    def __init__(self):
        self.results: list[ImportResult] = []
        self.container: Optional[ui.element] = None
        self.summary_label: Optional[ui.label] = None
        self.progress_bar: Optional[ui.linear_progress] = None
        self.table_body: Optional[ui.element] = None
    
    def create(self, results: Optional[list[ImportResult]] = None) -> None:
        """Create the import progress table UI.
        
        Args:
            results: Optional initial results to display
        """
        if results:
            self.results = results
        
        self.container = ui.column().classes("w-full")
        
        with self.container:
            # Summary header
            with ui.row().classes("w-full items-center justify-between mb-4"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("import_export", size="md").classes("text-blue-500")
                    self.summary_label = ui.label("Import Progress").classes("text-lg font-semibold")
                
                # Progress stats
                self.stats_container = ui.row().classes("gap-4")
                with self.stats_container:
                    self._create_stat_badge("pending", 0, "Pending")
                    self._create_stat_badge("success", 0, "Success")
                    self._create_stat_badge("failed", 0, "Failed")
            
            # Progress bar
            self.progress_bar = ui.linear_progress(value=0, show_value=False).classes("w-full mb-4")
            
            # Table
            with ui.card().classes("w-full"):
                with ui.element("div").classes("w-full overflow-x-auto max-h-[400px] overflow-y-auto"):
                    with ui.element("table").classes("w-full"):
                        # Header
                        with ui.element("thead").classes("bg-slate-100 dark:bg-slate-800 sticky top-0"):
                            with ui.element("tr"):
                                for header in ["Status", "Type", "Resource", "Target ID", "Duration"]:
                                    with ui.element("th").classes("px-3 py-2 text-left text-sm font-medium"):
                                        ui.label(header)
                        
                        # Body
                        self.table_body = ui.element("tbody")
                        
            # Initial render
            self._render_results()
    
    def _create_stat_badge(self, status: str, count: int, label: str) -> ui.element:
        """Create a status stat badge."""
        color = STATUS_COLORS.get(status, "#6B7280")
        with ui.row().classes("items-center gap-1"):
            ui.icon(STATUS_ICONS.get(status, "circle"), size="xs").style(f"color: {color};")
            badge = ui.badge(f"{count}", color=status if status != "pending" else "grey")
            ui.label(label).classes("text-sm text-slate-500")
        return badge
    
    def _render_results(self) -> None:
        """Render the current results in the table."""
        if not self.table_body:
            return
        
        self.table_body.clear()
        
        with self.table_body:
            for result in self.results:
                self._render_result_row(result)
        
        # Update summary
        self._update_summary()
    
    def _render_result_row(self, result: ImportResult) -> None:
        """Render a single result row."""
        color = STATUS_COLORS.get(result.status, "#6B7280")
        icon = STATUS_ICONS.get(result.status, "circle")
        
        with ui.element("tr").classes("border-b hover:bg-slate-50 dark:hover:bg-slate-800"):
            # Status
            with ui.element("td").classes("px-3 py-2"):
                with ui.row().classes("items-center gap-1"):
                    ui.icon(icon, size="xs").style(f"color: {color};")
                    ui.label(result.status.title()).classes("text-sm").style(f"color: {color};")
            
            # Type
            with ui.element("td").classes("px-3 py-2"):
                type_label = RESOURCE_TYPE_LABELS.get(result.resource_type, result.resource_type)
                ui.label(type_label).classes("text-sm")
            
            # Resource (address)
            with ui.element("td").classes("px-3 py-2"):
                # Show abbreviated address
                address = result.resource_address
                if len(address) > 50:
                    address = "..." + address[-47:]
                ui.label(address).classes("text-sm font-mono text-slate-600 dark:text-slate-400")
            
            # Target ID
            with ui.element("td").classes("px-3 py-2"):
                ui.label(str(result.target_id)).classes("text-sm")
            
            # Duration
            with ui.element("td").classes("px-3 py-2"):
                if result.duration_ms is not None:
                    duration_str = f"{result.duration_ms}ms"
                else:
                    duration_str = "-"
                ui.label(duration_str).classes("text-sm text-slate-500")
    
    def _update_summary(self) -> None:
        """Update summary stats and progress bar."""
        total = len(self.results)
        if total == 0:
            return
        
        success = sum(1 for r in self.results if r.status == "success")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        
        completed = success + failed + skipped
        progress = completed / total if total > 0 else 0
        
        if self.progress_bar:
            self.progress_bar.set_value(progress)
        
        if self.summary_label:
            self.summary_label.text = f"Import Progress ({completed}/{total})"
    
    def update_result(self, result: ImportResult) -> None:
        """Update a single result and refresh the display.
        
        Args:
            result: The updated result
        """
        # Find and update the result
        for i, r in enumerate(self.results):
            if r.source_key == result.source_key:
                self.results[i] = result
                break
        else:
            # Not found, add it
            self.results.append(result)
        
        # Re-render
        self._render_results()
    
    def set_results(self, results: list[ImportResult]) -> None:
        """Set all results and refresh.
        
        Args:
            results: New list of results
        """
        self.results = results
        self._render_results()


def create_import_summary_card(summary: ImportSummary) -> None:
    """Create a summary card for completed import operation.
    
    Args:
        summary: The import summary to display
    """
    success_rate = (summary.success / summary.total * 100) if summary.total > 0 else 0
    duration_sec = summary.duration_ms / 1000 if summary.duration_ms else 0
    
    with ui.card().classes("w-full p-4"):
        with ui.row().classes("w-full items-center justify-between"):
            # Title
            with ui.row().classes("items-center gap-2"):
                icon = "check_circle" if summary.failed == 0 else "warning"
                color = "#22C55E" if summary.failed == 0 else "#F59E0B"
                ui.icon(icon, size="lg").style(f"color: {color};")
                ui.label("Import Complete").classes("text-xl font-semibold")
            
            # Duration
            ui.label(f"Duration: {duration_sec:.1f}s").classes("text-slate-500")
        
        # Stats grid
        with ui.row().classes("w-full mt-4 gap-4"):
            with ui.card().classes("p-3 flex-1"):
                ui.label(str(summary.total)).classes("text-2xl font-bold")
                ui.label("Total").classes("text-sm text-slate-500")
            
            with ui.card().classes("p-3 flex-1 border-l-4 border-green-500"):
                ui.label(str(summary.success)).classes("text-2xl font-bold text-green-600")
                ui.label("Success").classes("text-sm text-slate-500")
            
            if summary.failed > 0:
                with ui.card().classes("p-3 flex-1 border-l-4 border-red-500"):
                    ui.label(str(summary.failed)).classes("text-2xl font-bold text-red-600")
                    ui.label("Failed").classes("text-sm text-slate-500")
            
            if summary.skipped > 0:
                with ui.card().classes("p-3 flex-1 border-l-4 border-yellow-500"):
                    ui.label(str(summary.skipped)).classes("text-2xl font-bold text-yellow-600")
                    ui.label("Skipped").classes("text-sm text-slate-500")
        
        # Success rate
        ui.label(f"Success Rate: {success_rate:.1f}%").classes("mt-4 text-slate-600 dark:text-slate-400")


def create_import_errors_expansion(failed_results: list[ImportResult]) -> None:
    """Create an expansion panel showing import errors.
    
    Args:
        failed_results: List of failed import results
    """
    if not failed_results:
        return
    
    with ui.expansion(
        f"Failed Imports ({len(failed_results)})",
        icon="error",
    ).classes("w-full").props("dense header-class=text-red-600"):
        for result in failed_results:
            with ui.card().classes("w-full p-3 mb-2 border-l-4 border-red-500"):
                ui.label(result.resource_address).classes("font-mono text-sm font-semibold")
                ui.label(f"Target ID: {result.target_id}").classes("text-sm text-slate-500")
                
                if result.error_message:
                    with ui.expansion("Error Details", icon="info").classes("w-full mt-2").props("dense"):
                        ui.code(result.error_message).classes("w-full text-xs")
