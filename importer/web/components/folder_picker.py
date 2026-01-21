"""Folder picker modal component for directory selection."""

from pathlib import Path
from typing import Callable, Optional

from nicegui import ui


def create_folder_picker_dialog(
    initial_path: str = ".",
    title: str = "Select Folder",
    on_select: Optional[Callable[[str], None]] = None,
) -> ui.dialog:
    """Create a dialog for browsing and selecting folders.
    
    Args:
        initial_path: Starting directory path
        title: Dialog title
        on_select: Callback when a folder is selected
        
    Returns:
        The dialog element (call .open() to show it)
    """
    # Resolve initial path
    try:
        current_path = Path(initial_path).resolve()
        if not current_path.exists():
            current_path = Path.cwd()
    except Exception:
        current_path = Path.cwd()
    
    # State
    picker_state = {
        "current_path": current_path,
        "selected_path": None,
    }
    
    with ui.dialog() as dialog:
        dialog.props("persistent")
        
        with ui.card().classes("w-full max-w-2xl").style("min-height: 500px;"):
            # Header
            with ui.row().classes("w-full items-center justify-between mb-4"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("folder_open", size="lg").classes("text-orange-500")
                    ui.label(title).classes("text-xl font-bold")
                ui.button(icon="close", on_click=dialog.close).props("flat round")
            
            # Path input/display
            path_input = ui.input(
                label="Current Path",
                value=str(picker_state["current_path"]),
            ).classes("w-full mb-2").props("outlined dense")
            
            # Breadcrumb navigation
            breadcrumb_row = ui.row().classes("w-full items-center gap-1 mb-2 flex-wrap")
            
            def update_breadcrumbs():
                breadcrumb_row.clear()
                with breadcrumb_row:
                    parts = picker_state["current_path"].parts
                    for i, part in enumerate(parts):
                        if i > 0:
                            ui.icon("chevron_right", size="xs").classes("text-slate-400")
                        
                        # Build path up to this part
                        part_path = Path(*parts[:i+1])
                        
                        # Make clickable
                        ui.button(
                            part if part != "/" else "Root",
                            on_click=lambda p=part_path: navigate_to(p),
                        ).props("flat dense size=sm").classes("min-w-0")
            
            # Directory listing
            dir_container = ui.scroll_area().classes("w-full border rounded").style("height: 300px;")
            
            def navigate_to(path: Path):
                """Navigate to a directory."""
                try:
                    resolved = path.resolve()
                    if resolved.is_dir():
                        picker_state["current_path"] = resolved
                        picker_state["selected_path"] = resolved
                        path_input.value = str(resolved)
                        update_directory_listing()
                        update_breadcrumbs()
                except Exception as e:
                    ui.notify(f"Cannot access: {e}", type="warning")
            
            def update_directory_listing():
                """Update the directory listing."""
                dir_container.clear()
                current = picker_state["current_path"]
                
                with dir_container:
                    with ui.column().classes("w-full p-2 gap-1"):
                        # Parent directory option
                        if current.parent != current:
                            with ui.row().classes(
                                "w-full items-center gap-2 p-2 rounded cursor-pointer "
                                "hover:bg-slate-100 dark:hover:bg-slate-800"
                            ).on("click", lambda: navigate_to(current.parent)):
                                ui.icon("folder", size="sm").classes("text-amber-500")
                                ui.label("..").classes("font-medium")
                                ui.label("(Parent Directory)").classes("text-sm text-slate-500")
                        
                        # List directories
                        try:
                            entries = sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
                            dirs_found = False
                            
                            for entry in entries:
                                # Only show directories, skip hidden
                                if entry.is_dir() and not entry.name.startswith("."):
                                    dirs_found = True
                                    
                                    def select_dir(p=entry):
                                        picker_state["selected_path"] = p
                                        path_input.value = str(p)
                                        # Visual selection feedback
                                        update_directory_listing()
                                    
                                    def enter_dir(p=entry):
                                        navigate_to(p)
                                    
                                    is_selected = picker_state["selected_path"] == entry
                                    bg_class = "bg-orange-100 dark:bg-orange-900/30" if is_selected else ""
                                    
                                    with ui.row().classes(
                                        f"w-full items-center gap-2 p-2 rounded cursor-pointer "
                                        f"hover:bg-slate-100 dark:hover:bg-slate-800 {bg_class}"
                                    ).on("click", select_dir).on("dblclick", enter_dir):
                                        ui.icon("folder", size="sm").classes("text-amber-500")
                                        ui.label(entry.name).classes("font-medium flex-grow truncate")
                                        
                                        # Show entry button
                                        ui.button(
                                            icon="chevron_right",
                                            on_click=lambda p=entry: navigate_to(p),
                                        ).props("flat dense round size=xs")
                            
                            if not dirs_found:
                                ui.label("No subdirectories").classes("text-slate-500 italic p-4")
                                
                        except PermissionError:
                            ui.label("Permission denied").classes("text-red-500 p-4")
                        except Exception as e:
                            ui.label(f"Error: {e}").classes("text-red-500 p-4")
            
            # Handle manual path input
            def on_path_change(e):
                try:
                    new_path = Path(e.value).resolve()
                    if new_path.is_dir():
                        picker_state["current_path"] = new_path
                        picker_state["selected_path"] = new_path
                        update_directory_listing()
                        update_breadcrumbs()
                except Exception:
                    pass  # Invalid path, ignore
            
            path_input.on("change", on_path_change)
            
            # Quick navigation buttons
            with ui.row().classes("w-full gap-2 mt-2"):
                ui.button(
                    "Home",
                    icon="home",
                    on_click=lambda: navigate_to(Path.home()),
                ).props("flat dense size=sm")
                
                ui.button(
                    "Current Dir",
                    icon="folder",
                    on_click=lambda: navigate_to(Path.cwd()),
                ).props("flat dense size=sm")
                
                # New folder button
                def create_new_folder():
                    with ui.dialog() as new_folder_dialog:
                        with ui.card().classes("p-4"):
                            ui.label("Create New Folder").classes("font-semibold mb-2")
                            folder_name = ui.input(label="Folder Name").classes("w-full")
                            
                            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                                ui.button("Cancel", on_click=new_folder_dialog.close).props("flat")
                                
                                def do_create():
                                    if folder_name.value:
                                        try:
                                            new_path = picker_state["current_path"] / folder_name.value
                                            new_path.mkdir(parents=True, exist_ok=True)
                                            ui.notify(f"Created: {folder_name.value}", type="positive")
                                            new_folder_dialog.close()
                                            update_directory_listing()
                                        except Exception as e:
                                            ui.notify(f"Error: {e}", type="negative")
                                
                                ui.button("Create", on_click=do_create).props("color=primary")
                    
                    new_folder_dialog.open()
                
                ui.button(
                    "New Folder",
                    icon="create_new_folder",
                    on_click=create_new_folder,
                ).props("flat dense size=sm")
            
            # Action buttons
            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                
                def confirm_selection():
                    selected = picker_state["selected_path"] or picker_state["current_path"]
                    if on_select:
                        on_select(str(selected))
                    dialog.close()
                
                ui.button(
                    "Select",
                    icon="check",
                    on_click=confirm_selection,
                ).props("color=primary")
            
            # Initialize
            update_breadcrumbs()
            update_directory_listing()
    
    return dialog
