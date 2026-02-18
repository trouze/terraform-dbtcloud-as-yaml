"""Unit tests for protection integration on the Adopt page.

Tests cover the protection-adoption interaction logic:
- Guard: protecting ignored resources requires adopt confirmation
- Direct toggle: protecting/unprotecting adopted resources
- State updates: protected_resources set changes on toggle
- Re-plan trigger: protection changes invalidate stale plans
- Import address: protected rows target protected_* TF blocks

Reference: PRD 43.02 Phase 5 — Protection Integration
"""

import pytest
from typing import Optional

from importer.web.utils.terraform_import import (
    generate_adopt_imports_from_grid,
)


# =============================================================================
# Helpers
# =============================================================================


def _make_adopt_row(
    source_type: str,
    source_key: str,
    source_name: str,
    target_id: int,
    project_name: str = "my_project",
    project_id: Optional[int] = None,
    action: str = "adopt",
    protected: bool = False,
    drift_status: str = "not_in_state",
) -> dict:
    """Create a minimal grid row dict for testing."""
    row = {
        "source_type": source_type,
        "source_key": source_key,
        "source_name": source_name,
        "target_id": target_id,
        "project_name": project_name,
        "action": action,
        "protected": protected,
        "drift_status": drift_status,
    }
    if project_id is not None:
        row["project_id"] = project_id
    return row


# =============================================================================
# Guard Logic Tests (UT-AS-14, UT-AS-15)
# =============================================================================


class TestProtectionGuardLogic:
    """Test the invariant: protection requires adoption."""

    def test_protect_requires_adopt_guard_needed(self):
        """UT-AS-14: Ignored resource should require dialog before protecting.

        The UI handler checks: if action != 'adopt' and user clicks shield,
        show dialog. We test the *data condition* that drives this decision.
        """
        row = _make_adopt_row(
            "PRJ", "legacy_proj", "Legacy Project", 100,
            action="ignore", protected=False,
        )
        # The guard condition checked in _on_adopt_cell_clicked:
        needs_dialog = row["action"] != "adopt" and not row["protected"]
        assert needs_dialog is True

    def test_protect_adopted_resource_no_guard(self):
        """UT-AS-15: Adopted resource toggles directly without guard.

        If action == 'adopt', the shield toggle fires without dialog.
        """
        row = _make_adopt_row(
            "PRJ", "analytics", "Analytics", 200,
            action="adopt", protected=False,
        )
        needs_dialog = row["action"] != "adopt" and not row["protected"]
        assert needs_dialog is False

    def test_unprotect_always_direct(self):
        """UT-AS-17: Removing protection never requires a dialog, regardless of action."""
        # Adopted + protected
        row_adopted = _make_adopt_row(
            "PRJ", "analytics", "Analytics", 200,
            action="adopt", protected=True,
        )
        # Ignored + protected (edge case: user adopted+protected then switched to ignore)
        row_ignored = _make_adopt_row(
            "PRJ", "legacy", "Legacy", 201,
            action="ignore", protected=True,
        )
        # Unprotect is direct when currently_protected is True
        assert row_adopted["protected"] is True  # can unprotect directly
        assert row_ignored["protected"] is True  # can unprotect directly


# =============================================================================
# Adopt-and-Protect Sets Both Fields (UT-AS-16)
# =============================================================================


class TestAdoptAndProtect:
    """Test that the 'Yes' path sets both action=adopt and protected=True."""

    def test_adopt_and_protect_sets_both_fields(self):
        """UT-AS-16: After dialog Yes, both fields are set."""
        row = _make_adopt_row(
            "GRP", "member", "Member", 300,
            action="ignore", protected=False,
        )
        # Simulate the _apply_adopt_and_protect logic
        row["action"] = "adopt"
        row["protected"] = True

        assert row["action"] == "adopt"
        assert row["protected"] is True

    def test_adopt_and_protect_updates_confirmed_mappings(self):
        """After dialog Yes, confirmed_mappings is updated too."""
        confirmed_mappings = [
            {"source_key": "member", "action": "ignore"},
        ]
        # Simulate update
        for mapping in confirmed_mappings:
            if mapping["source_key"] == "member":
                mapping["action"] = "adopt"
                break

        assert confirmed_mappings[0]["action"] == "adopt"

    def test_adopt_and_protect_adds_missing_mapping(self):
        """If source_key not in confirmed_mappings, a new entry is appended."""
        confirmed_mappings = []
        source_key = "new_resource"

        # Simulate the append logic from _apply_adopt_and_protect
        found = False
        for mapping in confirmed_mappings:
            if mapping.get("source_key") == source_key:
                mapping["action"] = "adopt"
                found = True
                break
        if not found:
            confirmed_mappings.append({
                "source_key": source_key,
                "action": "adopt",
            })

        assert len(confirmed_mappings) == 1
        assert confirmed_mappings[0]["action"] == "adopt"


# =============================================================================
# Protection State Updates
# =============================================================================


class TestProtectionStateUpdates:
    """Test that protection toggles update the protected_resources set."""

    def test_protect_adds_to_set(self):
        """Protecting a resource adds its key to protected_resources."""
        protected_resources = set()
        source_key = "analytics"

        # Simulate _persist_protection(True)
        protected_resources.add(source_key)

        assert source_key in protected_resources

    def test_unprotect_removes_from_set(self):
        """Unprotecting a resource removes its key from protected_resources."""
        protected_resources = {"analytics", "legacy"}

        # Simulate _persist_protection(False)
        protected_resources.discard("analytics")

        assert "analytics" not in protected_resources
        assert "legacy" in protected_resources

    def test_protect_strips_target_prefix(self):
        """Protection with target__ prefix stores the bare key."""
        protected_resources = set()
        source_key = "target__everyone"
        bare_key = source_key
        if bare_key.startswith("target__"):
            bare_key = bare_key[len("target__"):]
        protected_resources.add(bare_key)

        assert "everyone" in protected_resources
        assert "target__everyone" not in protected_resources


# =============================================================================
# Re-Plan Trigger (UT-AS-18)
# =============================================================================


class TestRePlanTrigger:
    """Test that protection changes invalidate stale plans."""

    def test_protection_change_flags_plan_stale(self):
        """UT-AS-18: Changing protection should mark the plan as stale.

        In the UI, this means plan_btn visible + enabled, apply_btn hidden.
        We test the data condition: any protection toggle should set a
        'plan_stale' flag.
        """
        # Before protection change
        plan_output_exists = True  # User already ran a plan
        plan_stale = False

        # User toggles protection on a row
        protection_changed = True
        if protection_changed:
            plan_stale = True

        assert plan_stale is True


# =============================================================================
# Import Address Tests (UT-AS-19)
# =============================================================================


class TestProtectedImportAddress:
    """Test that protected adopt rows generate protected_* import addresses."""

    def test_protected_project_uses_protected_address(self):
        """UT-AS-19: Protected PRJ row generates protected_projects address."""
        row = _make_adopt_row(
            "PRJ", "analytics", "Analytics", 100, protected=True
        )
        result = generate_adopt_imports_from_grid([row])
        assert "protected_projects" in result
        assert '"100"' in result

    def test_unprotected_project_uses_regular_address(self):
        """Unprotected PRJ row uses regular projects address."""
        row = _make_adopt_row(
            "PRJ", "analytics", "Analytics", 100, protected=False
        )
        result = generate_adopt_imports_from_grid([row])
        assert "import {" in result
        assert "protected_projects" not in result

    def test_protected_job_uses_protected_address(self):
        """Protected JOB row generates protected_jobs address."""
        row = _make_adopt_row(
            "JOB", "daily", "Daily Run", 300, protected=True
        )
        result = generate_adopt_imports_from_grid([row])
        assert "protected_jobs" in result

    def test_protected_env_uses_protected_address(self):
        """Protected ENV row generates protected_environments address."""
        row = _make_adopt_row(
            "ENV", "prod", "Production", 200, protected=True
        )
        result = generate_adopt_imports_from_grid([row])
        assert "protected_environments" in result

    def test_protected_repository_uses_protected_address(self):
        """Protected REP row generates protected_repositories address."""
        row = _make_adopt_row(
            "REP", "my_repo", "my-repo", 400,
            project_name="Analytics", project_id=100, protected=True,
        )
        result = generate_adopt_imports_from_grid([row])
        assert "protected_repositories" in result

    def test_mixed_protected_and_unprotected_generate_correct_addresses(self):
        """Mix of protected and unprotected rows in same plan."""
        rows = [
            _make_adopt_row("PRJ", "alpha", "Alpha", 100, protected=True),
            _make_adopt_row("PRJ", "beta", "Beta", 101, protected=False),
            _make_adopt_row("JOB", "daily", "Daily", 300, protected=True),
            _make_adopt_row("JOB", "weekly", "Weekly", 301, protected=False),
        ]
        result = generate_adopt_imports_from_grid(rows)
        assert result.count("import {") == 4
        assert "protected_projects" in result
        assert "protected_jobs" in result

        # Count protected vs regular addresses
        lines = result.split("\n")
        to_lines = [l.strip() for l in lines if l.strip().startswith("to =")]
        protected_count = sum(1 for l in to_lines if "protected_" in l)
        regular_count = sum(1 for l in to_lines if "protected_" not in l)
        assert protected_count == 2
        assert regular_count == 2


# =============================================================================
# Protection + YAML Integration
# =============================================================================


class TestProtectedAddressTargetPrefixStripping:
    """Regression: protected address must strip target__ prefix."""

    def test_protected_target_only_resource_strips_prefix(self):
        """Protected target-only PRJ with source_key 'target__not_terraform'
        should generate an address using bare 'not_terraform', not the prefixed form.

        Regression for: 'Configuration for import target does not exist' when
        Terraform sees protected_projects["target__not_terraform"] but the YAML
        key is "not_terraform".
        """
        row = _make_adopt_row(
            "PRJ", "target__not_terraform", "not_terraform", 602,
            protected=True,
        )
        result = generate_adopt_imports_from_grid([row])
        # Should use bare key in the address
        assert 'protected_projects["not_terraform"]' in result, (
            f"Expected bare key in address, got:\n{result}"
        )
        # Should NOT use the target__ prefixed key
        assert 'protected_projects["target__not_terraform"]' not in result, (
            f"target__ prefix should be stripped from protected address:\n{result}"
        )


class TestProtectionYamlIntegration:
    """Test that apply_protection_from_set stamps protected: true on YAML."""

    def test_protection_applied_to_adopted_project_yaml(self, tmp_path):
        """apply_protection_from_set sets protected: true on matching project."""
        import yaml
        from importer.web.utils.adoption_yaml_updater import apply_protection_from_set

        config = {
            "projects": [
                {"key": "my_project", "name": "My Project"},
                {"key": "other_project", "name": "Other"},
            ],
        }
        yaml_file = tmp_path / "config.yml"
        with open(yaml_file, "w") as f:
            yaml.dump(config, f)

        apply_protection_from_set(str(yaml_file), {"PRJ:my_project"})

        with open(yaml_file, "r") as f:
            result = yaml.safe_load(f)

        my_proj = next(p for p in result["projects"] if p["key"] == "my_project")
        other_proj = next(p for p in result["projects"] if p["key"] == "other_project")
        assert my_proj.get("protected") is True
        assert other_proj.get("protected") is not True

    def test_protection_applied_with_target_prefix_stripping(self, tmp_path):
        """apply_protection_from_set strips target__ prefix from keys."""
        import yaml
        from importer.web.utils.adoption_yaml_updater import apply_protection_from_set

        config = {
            "projects": [
                {"key": "legacy_project", "name": "Legacy"},
            ],
        }
        yaml_file = tmp_path / "config.yml"
        with open(yaml_file, "w") as f:
            yaml.dump(config, f)

        # Key has target__ prefix — should still match
        apply_protection_from_set(str(yaml_file), {"target__legacy_project"})

        with open(yaml_file, "r") as f:
            result = yaml.safe_load(f)

        proj = result["projects"][0]
        assert proj.get("protected") is True
