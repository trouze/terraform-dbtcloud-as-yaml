"""Adoption workflow preferences.

Stores project-level preferences for the adoption workflow in
``.magellan/adoption_preferences.json``. Reusable for both the
current Migration workflow and the future Import & Adopt workflow.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AdoptionPreferenceManager:
    """Manages adoption workflow preferences at the project level.
    
    Preferences are stored in ``.magellan/adoption_preferences.json``
    within the project directory. The file is JSON with the following
    shape::
    
        {
            "show_target_only": true,
            "first_run_shown": false
        }
    
    Attributes:
        project_dir: Path to the project directory (parent of .magellan/).
        show_target_only: Whether to show target-only resources by default.
        first_run_shown: Whether the first-run dialog has been shown.
    """
    
    DEFAULT_PREFS = {
        "show_target_only": True,
        "first_run_shown": False,
    }
    
    def __init__(self, project_dir: Optional[str] = None) -> None:
        self._project_dir = Path(project_dir) if project_dir else None
        self._prefs: dict = dict(self.DEFAULT_PREFS)
        self._loaded = False
    
    @property
    def file_path(self) -> Optional[Path]:
        """Path to the preferences file, or None if no project_dir."""
        if self._project_dir is None:
            return None
        return self._project_dir / ".magellan" / "adoption_preferences.json"
    
    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    
    @property
    def show_target_only(self) -> bool:
        """Whether target-only resources should be visible by default."""
        self._ensure_loaded()
        return bool(self._prefs.get("show_target_only", True))
    
    @show_target_only.setter
    def show_target_only(self, value: bool) -> None:
        self._ensure_loaded()
        self._prefs["show_target_only"] = value
    
    @property
    def first_run_shown(self) -> bool:
        """Whether the first-run dialog has been shown in this project."""
        self._ensure_loaded()
        return bool(self._prefs.get("first_run_shown", False))
    
    @first_run_shown.setter
    def first_run_shown(self, value: bool) -> None:
        self._ensure_loaded()
        self._prefs["first_run_shown"] = value
    
    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    
    def _ensure_loaded(self) -> None:
        """Lazy-load preferences from disk on first access."""
        if not self._loaded:
            self.load()
    
    def load(self) -> None:
        """Load preferences from disk. Missing file → defaults."""
        self._loaded = True
        path = self.file_path
        if path is None or not path.exists():
            self._prefs = dict(self.DEFAULT_PREFS)
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                merged = dict(self.DEFAULT_PREFS)
                merged.update(data)
                self._prefs = merged
            else:
                self._prefs = dict(self.DEFAULT_PREFS)
        except Exception as exc:
            logger.warning("Failed to load adoption preferences: %s", exc)
            self._prefs = dict(self.DEFAULT_PREFS)
    
    def save(self) -> None:
        """Write current preferences to disk."""
        path = self.file_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self._prefs, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Failed to save adoption preferences: %s", exc)
    
    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    
    def should_show_first_run_dialog(self, has_target_only_rows: bool) -> bool:
        """Return True if the first-run dialog should be shown.
        
        Conditions:
        1. There are unmatched target-only resources
        2. The dialog hasn't been shown yet for this project
        """
        return has_target_only_rows and not self.first_run_shown
    
    def mark_first_run_shown(self, user_choice_show: bool, remember: bool = False) -> None:
        """Record the user's choice from the first-run dialog.
        
        Args:
            user_choice_show: True if user wants to see target-only resources
            remember: If True, persist as project-level preference
        """
        self.first_run_shown = True
        if remember:
            self.show_target_only = user_choice_show
        self.save()
