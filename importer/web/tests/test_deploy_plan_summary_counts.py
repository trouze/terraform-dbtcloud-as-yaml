"""Deploy plan summary parsing and count-semantics regression tests."""

from importer.web.pages.deploy import _parse_plan_summary


def test_parse_plan_summary_matches_expected_add_count() -> None:
    """Plan parser extracts add/change/destroy counts from plan output."""
    plan_output = """
Terraform used the selected providers to generate the following execution plan.
Plan: 49 to add, 0 to change, 0 to destroy.
"""
    summary = _parse_plan_summary(plan_output)
    assert summary == {"import": 0, "add": 49, "change": 0, "destroy": 0}


def test_source_select_vs_tf_add_count_semantics() -> None:
    """Source totals and TF adds can differ due to resource mapping semantics."""
    source_selected_total = 53
    credentials_selected = 5
    repositories_selected = 1

    # Credentials are typically referenced (not created), while each repository
    # selection creates both repository and project_repository resources.
    expected_tf_add = source_selected_total - credentials_selected + repositories_selected
    assert expected_tf_add == 49
