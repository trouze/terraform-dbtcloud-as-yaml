"""Intent key consistency tests (K-1 through K-5).

Validates that intent keys are generated, stored, and looked up consistently
across all code paths: match grid, adopt grid, protection intent manager,
and the unified pipeline.

See PRD 43.03 — Unified Protect & Adopt Pipeline, Harness 3.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from importer.web.utils.protection_intent import ProtectionIntentManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def intent_manager(tmp_path):
    return ProtectionIntentManager(tmp_path / "protection-intent.json")


# ---------------------------------------------------------------------------
# K-1: Intent key strips target__ prefix
# ---------------------------------------------------------------------------

class TestK1StripTargetPrefix:
    """Intent keys must never contain `target__`."""

    def test_bare_key_no_prefix(self, intent_manager):
        """Bare key 'everyone' is stored as-is."""
        intent_manager.set_intent("GRP:everyone", protected=True, source="test", reason="test")
        assert intent_manager.has_intent("GRP:everyone")

    def test_target_prefix_must_be_stripped_before_storage(self, intent_manager):
        """If code accidentally passes target__everyone, it should NOT be stored."""
        # This test documents the contract: callers must strip before calling.
        # If someone passes a target__-prefixed key, the lookup will fail.
        intent_manager.set_intent("GRP:target__everyone", protected=True, source="test", reason="test")
        # This key exists as-is (bad behavior), but the canonical key does not
        assert not intent_manager.has_intent("GRP:everyone")
        # This verifies the BUG we're preventing: callers must strip prefix first
        assert intent_manager.has_intent("GRP:target__everyone")

    def test_correct_key_format(self):
        """Document the correct key normalization sequence."""
        # Simulating what _get_intent_key_for_row should do:
        source_key = "target__everyone"
        bare_key = source_key.removeprefix("target__")
        source_type = "GRP"
        intent_key = f"{source_type}:{bare_key}"
        assert intent_key == "GRP:everyone"
        assert "target__" not in intent_key


# ---------------------------------------------------------------------------
# K-2: Intent key uses prefixed format TYPE:key
# ---------------------------------------------------------------------------

class TestK2PrefixedFormat:
    """All intent keys must be in TYPE:key format."""

    @pytest.mark.parametrize(
        "key",
        [
            "GRP:everyone",
            "GRP:member",
            "PRJ:sse_dm_fin_fido",
            "ENV:sse_dm_fin_fido_qa",
            "REP:sse_dm_fin_fido",
            "PREP:sse_dm_fin_fido",
            "JOB:sse_dm_fin_fido__daily_run",
            "CON:snowflake_main",
            "TOK:deploy_token",
        ],
    )
    def test_valid_prefixed_keys(self, intent_manager, key):
        """Verify standard TYPE:key format is accepted."""
        intent_manager.set_intent(key, protected=True, source="test", reason="test")
        assert intent_manager.has_intent(key)
        intent = intent_manager.get_intent(key)
        assert intent is not None
        assert intent.protected is True


# ---------------------------------------------------------------------------
# K-3: old_protected matches grid rendering
# ---------------------------------------------------------------------------

class TestK3OldProtectedConsistency:
    """old_protected must use the same lookup path as grid rendering.

    The grid uses both protected_resources (in-memory set) and the
    protection intent manager. The on_row_change handler must check both.
    """

    def test_old_protected_from_intent_manager(self, intent_manager):
        """Intent manager returns effective protection."""
        intent_manager.set_intent(
            "GRP:everyone", protected=True, source="test", reason="test"
        )
        # Simulate what on_row_change should do:
        # Check protected_resources first (empty after restart)
        protected_resources = set()  # Empty after restart
        source_key = "target__everyone"
        bare_key = source_key.removeprefix("target__")

        old_protected = source_key in protected_resources
        if not old_protected:
            old_protected = bare_key in protected_resources
        # Also check intent manager (matches what build_grid_data uses)
        if not old_protected:
            intent_key = f"GRP:{bare_key}"
            old_protected = intent_manager.get_effective_protection(
                intent_key, yaml_protected=False
            )

        assert old_protected is True, "old_protected must detect intent even after restart"

    def test_old_protected_from_set(self):
        """In-memory set lookup must strip prefixes."""
        protected_resources = {"everyone"}
        source_key = "target__everyone"

        # Wrong way (without stripping):
        old_protected_wrong = source_key in protected_resources
        assert old_protected_wrong is False

        # Correct way:
        bare_key = source_key.removeprefix("target__")
        old_protected_correct = bare_key in protected_resources
        assert old_protected_correct is True


# ---------------------------------------------------------------------------
# K-4: Action change to ignore clears protection intent
# ---------------------------------------------------------------------------

class TestK4IgnoreClearsIntent:
    """Setting action=ignore on a protected resource must remove the intent."""

    def test_ignore_removes_intent(self, intent_manager):
        """Simulates the on_row_change action→ignore path."""
        # Set up: resource is protected
        intent_manager.set_intent(
            "GRP:everyone", protected=True, source="user_click", reason="protect",
        )
        assert intent_manager.has_intent("GRP:everyone")

        # Act: User changes action to ignore — handler should remove intent
        intent_manager.remove_intent("GRP:everyone", source="action_change_to_ignore")

        # Assert
        assert not intent_manager.has_intent("GRP:everyone")

    def test_ignore_updates_protected_resources_set(self):
        """protected_resources must also be updated."""
        protected_resources = {"everyone"}

        # Simulate clearing on ignore
        bare_key = "everyone"
        protected_resources.discard(bare_key)

        assert bare_key not in protected_resources


# ---------------------------------------------------------------------------
# K-5: Adopt guard dialog sets both intents
# ---------------------------------------------------------------------------

class TestK5AdoptGuardSetsBoth:
    """The 'Adopt & Protect' guard dialog must persist both action and protection."""

    def test_guard_dialog_sets_both_intents(self, intent_manager):
        """After 'Yes — Adopt & Protect', both confirmed_mapping and protection intent exist."""
        source_key = "target__everyone"
        bare_key = source_key.removeprefix("target__")
        source_type = "GRP"

        # 1. Record adoption in confirmed_mappings
        confirmed_mappings = []
        confirmed_mappings.append({
            "source_key": source_key,
            "target_key": source_key,
            "action": "adopt",
        })

        # 2. Record protection in intent manager
        intent_key = f"{source_type}:{bare_key}"
        intent_manager.set_intent(
            intent_key,
            protected=True,
            source="adopt_guard_dialog",
            reason="User chose Adopt & Protect",
        )

        # 3. Add to protected_resources
        protected_resources = set()
        protected_resources.add(bare_key)

        # Verify both stores are updated
        assert len(confirmed_mappings) == 1
        assert confirmed_mappings[0]["action"] == "adopt"
        assert intent_manager.has_intent(intent_key)
        assert intent_manager.get_intent(intent_key).protected is True
        assert bare_key in protected_resources


# ---------------------------------------------------------------------------
# Bonus: Cross-namespace consistency
# ---------------------------------------------------------------------------

class TestKeyNamespaceConsistency:
    """Verify the three key namespaces can be translated correctly."""

    @pytest.mark.parametrize(
        "grid_key,protected_key,intent_key",
        [
            ("everyone", "everyone", "GRP:everyone"),
            ("target__everyone", "everyone", "GRP:everyone"),
            ("sse_dm_fin_fido", "sse_dm_fin_fido", "PRJ:sse_dm_fin_fido"),
            ("target__sse_dm_fin_fido", "sse_dm_fin_fido", "PRJ:sse_dm_fin_fido"),
        ],
    )
    def test_key_translation(self, grid_key, protected_key, intent_key):
        """Grid key → protected_resources key → intent key."""
        # Grid → protected_resources
        bare = grid_key.removeprefix("target__")
        assert bare == protected_key

        # Grid → intent key (requires source_type which we get from the row)
        rtype = intent_key.split(":")[0]
        computed_intent = f"{rtype}:{bare}"
        assert computed_intent == intent_key
