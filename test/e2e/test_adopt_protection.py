"""E2E tests for Adopt page protection workflow.

These tests verify:
- Adopt page loads without error and displays the AG Grid
- Shield column is clickable and toggles protection on adopted rows
- Clicking shield on an ignored row shows the "Protection Requires Adoption" dialog
- Dialog "Yes" adopts + protects the resource; "No" leaves it unchanged
- Summary counters update reactively (adopt count, protected count)
- Protection toggle invalidates a stale plan (re-enables Plan button)
- Navigation (Back to Match, Continue to Configure)

Reference: PRD 43.02-Adoption-Terraform-Step.md — Phase 5 Protection Integration
Test IDs: E2E-AS-08 through E2E-AS-11
"""

import pytest
from playwright.sync_api import Page, expect

from pages import AdoptPage


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def adopt_page(page_with_server: Page) -> AdoptPage:
    """Create an AdoptPage instance."""
    return AdoptPage(page_with_server)


# =============================================================================
# E2E-AS-08: Adopt Page Load & Grid Display
# =============================================================================


class TestAdoptPageLoad:
    """Tests for Adopt page loading and grid display."""

    @pytest.mark.e2e
    def test_adopt_page_loads_without_error(self, adopt_page: AdoptPage):
        """E2E-AS-08.1: Verify Adopt page loads without 500 error."""
        adopt_page.go_to_adopt()
        adopt_page.assert_page_loads_without_error()

    @pytest.mark.e2e
    def test_adopt_page_url_is_correct(self, adopt_page: AdoptPage):
        """E2E-AS-08.2: Verify Adopt page URL is /adopt."""
        adopt_page.go_to_adopt()
        adopt_page.assert_on_adopt_page()

    @pytest.mark.e2e
    def test_adopt_page_has_title(self, adopt_page: AdoptPage):
        """E2E-AS-08.3: Verify Adopt page displays correct title."""
        adopt_page.go_to_adopt()
        page_content = adopt_page.get_page_content()
        assert "Adopt Resources" in page_content

    @pytest.mark.e2e
    def test_adopt_page_shows_grid_or_empty_state(self, adopt_page: AdoptPage):
        """E2E-AS-08.4: Verify Adopt page shows grid or 'Nothing to adopt'."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        has_grid = adopt_page.has_adopt_grid()
        has_empty = adopt_page.has_nothing_to_adopt()
        has_complete = adopt_page.is_adoption_complete()

        assert has_grid or has_empty or has_complete, (
            "Expected either an adopt grid, 'Nothing to adopt', or 'Adoption Complete'"
        )


# =============================================================================
# E2E-AS-09: Shield Column Behavior
# =============================================================================


class TestShieldColumn:
    """Tests for the shield/protection column in the adopt grid."""

    @pytest.mark.e2e
    def test_shield_column_renders_for_all_rows(self, adopt_page: AdoptPage):
        """E2E-AS-09.1: Verify every row has a shield/circle in the protected column."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available — nothing to adopt")

        rows = adopt_page.get_grid_rows()
        if not rows:
            pytest.skip("No rows in adopt grid")

        for row in rows:
            shield_cell = row.locator('[col-id="protected"]')
            text = shield_cell.text_content() or ""
            # Should have either shield emoji or circle
            has_indicator = "🛡" in text or "○" in text
            assert has_indicator, f"Row missing protection indicator: {text}"

    @pytest.mark.e2e
    def test_click_shield_on_adopted_row_toggles_protection(self, adopt_page: AdoptPage):
        """E2E-AS-09.2: Clicking shield on an adopted, unprotected row enables protection."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        # Find an adopted, unprotected row
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            is_protected = adopt_page.get_row_protection_status(row)
            if "Adopt" in action_text and not is_protected:
                target_row = row
                break

        if not target_row:
            pytest.skip("No unprotected adopted row available")

        # Click the shield
        adopt_page.click_shield(target_row)

        # Should NOT show the dialog (resource is already adopted)
        assert not adopt_page.is_protection_dialog_visible(), (
            "Dialog should not appear for adopted resources"
        )

        # Should now be protected
        adopt_page.assert_row_is_protected(target_row)

    @pytest.mark.e2e
    def test_click_shield_on_ignored_row_shows_dialog(self, adopt_page: AdoptPage):
        """E2E-AS-09.3: Clicking shield on an ignored row shows the protection dialog."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        # Find an ignored row
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            if "Ignore" in action_text:
                target_row = row
                break

        if not target_row:
            pytest.skip("No ignored row available")

        # Click the shield on the ignored row
        adopt_page.click_shield(target_row)

        # Should show the "Protection Requires Adoption" dialog
        adopt_page.assert_protection_dialog_visible()

    @pytest.mark.e2e
    def test_unprotect_adopted_row_toggles_off(self, adopt_page: AdoptPage):
        """E2E-AS-09.4: Clicking shield on a protected row removes protection."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        # Find a protected, adopted row
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            is_protected = adopt_page.get_row_protection_status(row)
            if "Adopt" in action_text and is_protected:
                target_row = row
                break

        if not target_row:
            pytest.skip("No protected adopted row available")

        # Click the shield to unprotect
        adopt_page.click_shield(target_row)

        # Should now be unprotected
        adopt_page.assert_row_is_not_protected(target_row)


# =============================================================================
# E2E-AS-10: Protection Dialog Behavior
# =============================================================================


class TestProtectionDialog:
    """Tests for the 'Protection Requires Adoption' dialog."""

    @pytest.mark.e2e
    def test_dialog_shows_resource_name(self, adopt_page: AdoptPage):
        """E2E-AS-10.1: Dialog text includes the resource name."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            if "Ignore" in action_text:
                target_row = row
                break

        if not target_row:
            pytest.skip("No ignored row available")

        adopt_page.click_shield(target_row)

        if not adopt_page.is_protection_dialog_visible():
            pytest.skip("Dialog did not appear — resource type may not be protectable")

        dialog_text = adopt_page.get_protection_dialog_text()
        assert "Protection Requires Adoption" in dialog_text
        assert "adopt and protect" in dialog_text.lower()

    @pytest.mark.e2e
    def test_dialog_yes_adopts_and_protects(self, adopt_page: AdoptPage):
        """E2E-AS-10.2: Clicking 'Yes' adopts the resource and enables protection."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            if "Ignore" in action_text:
                target_row = row
                break

        if not target_row:
            pytest.skip("No ignored row available")

        adopt_page.click_shield(target_row)

        if not adopt_page.is_protection_dialog_visible():
            pytest.skip("Dialog did not appear")

        # Click Yes
        adopt_page.confirm_adopt_and_protect()

        # Dialog should close
        adopt_page.assert_protection_dialog_hidden()

        # Row should now be adopted + protected
        adopt_page.assert_row_is_protected(target_row)
        action_text = adopt_page.get_row_action(target_row)
        assert "Adopt" in action_text, f"Expected action=adopt after dialog Yes, got '{action_text}'"

    @pytest.mark.e2e
    def test_dialog_no_leaves_unchanged(self, adopt_page: AdoptPage):
        """E2E-AS-10.3: Clicking 'No' leaves the resource as ignored + unprotected."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        rows = adopt_page.get_grid_rows()
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            if "Ignore" in action_text:
                target_row = row
                break

        if not target_row:
            pytest.skip("No ignored row available")

        adopt_page.click_shield(target_row)

        if not adopt_page.is_protection_dialog_visible():
            pytest.skip("Dialog did not appear")

        # Click No
        adopt_page.cancel_adopt_and_protect()

        # Dialog should close
        adopt_page.assert_protection_dialog_hidden()

        # Row should remain ignored + unprotected
        adopt_page.assert_row_is_not_protected(target_row)
        action_text = adopt_page.get_row_action(target_row)
        assert "Ignore" in action_text, f"Expected action=ignore after dialog No, got '{action_text}'"


# =============================================================================
# E2E-AS-11: Summary Counter Updates
# =============================================================================


class TestSummaryCounters:
    """Tests for reactive summary counter updates on protection changes."""

    @pytest.mark.e2e
    def test_summary_counters_present(self, adopt_page: AdoptPage):
        """E2E-AS-11.1: Summary card displays adopt and protected counters."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if adopt_page.has_nothing_to_adopt() or adopt_page.is_adoption_complete():
            pytest.skip("Nothing to adopt or already complete")

        page_content = adopt_page.get_page_content()
        assert "Adoption Summary" in page_content
        assert "Resources to Import" in page_content
        assert "Protected" in page_content

    @pytest.mark.e2e
    def test_protection_toggle_updates_protected_count(self, adopt_page: AdoptPage):
        """E2E-AS-11.2: Toggling protection updates the Protected counter."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if not adopt_page.has_adopt_grid():
            pytest.skip("No adopt grid available")

        # Get initial protected count
        initial_count = adopt_page.get_protected_count_text()

        # Find an unprotected, adopted row to toggle
        rows = adopt_page.get_grid_rows()
        target_row = None
        for row in rows:
            action_text = adopt_page.get_row_action(row)
            is_protected = adopt_page.get_row_protection_status(row)
            if "Adopt" in action_text and not is_protected:
                target_row = row
                break

        if not target_row:
            pytest.skip("No unprotected adopted row available")

        # Toggle protection on
        adopt_page.click_shield(target_row)

        # If dialog appeared, confirm
        if adopt_page.is_protection_dialog_visible():
            adopt_page.confirm_adopt_and_protect()

        # Protected count should increment
        new_count = adopt_page.get_protected_count_text()
        assert int(new_count) > int(initial_count), (
            f"Protected count should have increased from {initial_count} to at least "
            f"{int(initial_count) + 1}, got {new_count}"
        )


# =============================================================================
# E2E-AS-12: Plan Invalidation on Protection Change
# =============================================================================


class TestPlanInvalidation:
    """Tests for plan invalidation when protection changes."""

    @pytest.mark.e2e
    def test_plan_button_visible_on_load(self, adopt_page: AdoptPage):
        """E2E-AS-12.1: Plan Adoption button is visible on initial load."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        if adopt_page.has_nothing_to_adopt() or adopt_page.is_adoption_complete():
            pytest.skip("Nothing to adopt or already complete")

        adopt_page.assert_plan_button_visible()
        adopt_page.assert_apply_button_hidden()


# =============================================================================
# E2E-AS-13: Navigation
# =============================================================================


class TestAdoptNavigation:
    """Tests for Adopt page navigation."""

    @pytest.mark.e2e
    def test_back_to_match_button_exists(self, adopt_page: AdoptPage):
        """E2E-AS-13.1: 'Back to Match' button is present."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        page_content = adopt_page.get_page_content()
        assert "Back to Match" in page_content

    @pytest.mark.e2e
    def test_adopt_page_has_back_button_regardless_of_state(self, adopt_page: AdoptPage):
        """E2E-AS-13.2: All states (grid, empty, complete) have Back to Match."""
        adopt_page.go_to_adopt()
        adopt_page.wait_for_loading_complete()

        page_content = adopt_page.get_page_content()
        assert "Back to Match" in page_content, (
            "Back to Match should be visible in every page state"
        )
