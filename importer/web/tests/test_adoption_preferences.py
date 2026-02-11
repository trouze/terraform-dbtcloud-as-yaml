"""Unit tests for AdoptionPreferenceManager.

Reference: PRD 43.01 — Criteria 13-14 (UT-AD-14, UT-AD-15)
"""

import json
import pytest
from pathlib import Path

from importer.web.utils.adoption_preferences import AdoptionPreferenceManager


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    return tmp_path


class TestAdoptionPreferenceDefaults:
    """Criterion 13: Default preferences are correct."""

    def test_default_show_target_only_is_true(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.show_target_only is True

    def test_default_first_run_shown_is_false(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.first_run_shown is False


class TestAdoptionPreferencePersistence:
    """Criterion 13: Preferences persist across loads."""

    def test_save_and_load_show_target_only(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.show_target_only = False
        mgr.save()

        mgr2 = AdoptionPreferenceManager(str(project_dir))
        assert mgr2.show_target_only is False

    def test_save_and_load_first_run_shown(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.first_run_shown = True
        mgr.save()

        mgr2 = AdoptionPreferenceManager(str(project_dir))
        assert mgr2.first_run_shown is True

    def test_file_created_in_magellan_dir(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.save()
        assert (project_dir / ".magellan" / "adoption_preferences.json").exists()

    def test_file_is_valid_json(self, project_dir):
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.show_target_only = False
        mgr.first_run_shown = True
        mgr.save()
        data = json.loads((project_dir / ".magellan" / "adoption_preferences.json").read_text())
        assert data["show_target_only"] is False
        assert data["first_run_shown"] is True


class TestFirstRunDialog:
    """Criterion 14: First-run dialog logic."""

    def test_should_show_when_target_only_and_not_shown(self, project_dir):
        """UT-AD-15: Dialog triggers when target-only exist and not yet shown."""
        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.should_show_first_run_dialog(has_target_only_rows=True) is True

    def test_should_not_show_when_no_target_only(self, project_dir):
        """UT-AD-15: Dialog does NOT trigger when no target-only rows."""
        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.should_show_first_run_dialog(has_target_only_rows=False) is False

    def test_should_not_show_when_already_shown(self, project_dir):
        """UT-AD-15: Dialog does NOT trigger after already shown."""
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.first_run_shown = True
        mgr.save()

        mgr2 = AdoptionPreferenceManager(str(project_dir))
        assert mgr2.should_show_first_run_dialog(has_target_only_rows=True) is False

    def test_mark_first_run_shown_without_remember(self, project_dir):
        """mark_first_run_shown without remember does not change show_target_only."""
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.mark_first_run_shown(user_choice_show=False, remember=False)
        assert mgr.first_run_shown is True
        # show_target_only stays default (True) since remember=False
        assert mgr.show_target_only is True

    def test_mark_first_run_shown_with_remember(self, project_dir):
        """mark_first_run_shown with remember=True persists the preference."""
        mgr = AdoptionPreferenceManager(str(project_dir))
        mgr.mark_first_run_shown(user_choice_show=False, remember=True)
        assert mgr.first_run_shown is True
        assert mgr.show_target_only is False
        # Verify it persisted
        mgr2 = AdoptionPreferenceManager(str(project_dir))
        assert mgr2.show_target_only is False
        assert mgr2.first_run_shown is True


class TestEdgeCases:
    """Edge cases for the preference manager."""

    def test_no_project_dir(self):
        """No project_dir → defaults, no file operations."""
        mgr = AdoptionPreferenceManager(None)
        assert mgr.show_target_only is True
        assert mgr.file_path is None
        mgr.save()  # Should not raise

    def test_corrupted_file_falls_back_to_defaults(self, project_dir):
        """Corrupted JSON file → defaults."""
        prefs_dir = project_dir / ".magellan"
        prefs_dir.mkdir(parents=True, exist_ok=True)
        (prefs_dir / "adoption_preferences.json").write_text("not json!")

        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.show_target_only is True  # default
        assert mgr.first_run_shown is False  # default

    def test_partial_file_merges_with_defaults(self, project_dir):
        """File with only some keys → missing keys get defaults."""
        prefs_dir = project_dir / ".magellan"
        prefs_dir.mkdir(parents=True, exist_ok=True)
        (prefs_dir / "adoption_preferences.json").write_text('{"show_target_only": false}')

        mgr = AdoptionPreferenceManager(str(project_dir))
        assert mgr.show_target_only is False
        assert mgr.first_run_shown is False  # default
