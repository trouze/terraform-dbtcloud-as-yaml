"""Tests for match diagnostic report text generation."""

from importer.web.components.entity_table import _build_llm_diagnostic


def test_crd_in_sync_diagnostic_does_not_report_no_state_key_match() -> None:
    report = _build_llm_diagnostic(
        source_key="c1dcfec236a5",
        source_name="Credential (snowflake)",
        source_type="CRD",
        source_id=None,
        project_name="Analytics",
        target_id="",
        target_name="Credential (snowflake)",
        state_id=None,
        state_address=None,
        state_resource_index=None,
        drift_status="in_sync",
        confidence="exact_match",
        action="match",
        is_protected=False,
        has_state_loaded=True,
        grid_row={"confidence": "exact_match", "status": "pending"},
        source_data={"environment_name": "Development"},
        state_resource=None,
        app_state=None,
    )

    assert "**CRD state is inherited from parent environment**" in report
    assert "- Match type: **crd_env_inherited**" in report
    assert "**No Terraform state tracking** - key comparison is not applicable." not in report
    assert "This is normal for resources that haven't been imported into Terraform yet" not in report


def test_crd_with_target_name_and_empty_id_reports_id_not_exposed() -> None:
    report = _build_llm_diagnostic(
        source_key="c1dcfec236a5",
        source_name="Credential (snowflake)",
        source_type="CRD",
        source_id=None,
        project_name="Analytics",
        target_id="",
        target_name="Credential (snowflake)",
        state_id=None,
        state_address=None,
        state_resource_index=None,
        drift_status="in_sync",
        confidence="env_match",
        action="match",
        is_protected=False,
        has_state_loaded=True,
        grid_row={"confidence": "env_match", "status": "pending"},
        source_data={"environment_name": "Development"},
        state_resource=None,
        app_state=None,
    )

    assert "- **Matched Target ID**: None (ID not exposed in report data)" in report
    assert (
        "2. **Credential by environment**: "
        '`target_crd_by_env[("Analytics", "Development")]`'
    ) in report


def test_crd_diagnostic_falls_back_to_grid_row_target_name() -> None:
    report = _build_llm_diagnostic(
        source_key="c1dcfec236a5",
        source_name="Credential (snowflake)",
        source_type="CRD",
        source_id=None,
        project_name="Analytics",
        target_id="",
        target_name="",
        state_id=None,
        state_address=None,
        state_resource_index=None,
        drift_status="in_sync",
        confidence="exact_match",
        action="match",
        is_protected=False,
        has_state_loaded=True,
        grid_row={
            "confidence": "exact_match",
            "status": "pending",
            "target_name": "Credential (snowflake)",
            "target_id": "",
        },
        source_data={"environment_name": "Development"},
        state_resource=None,
        app_state=None,
    )

    assert "- **Matched Target Name**: Credential (snowflake)" in report
    assert "- **Matched Target ID**: None (ID not exposed in report data)" in report
    assert (
        "CRD status is inherited from its parent environment, which is in sync."
        in report
    )
    assert "The Terraform state ID matches the target resource ID." not in report


def test_crd_env_parent_match_reports_parent_env_state_context() -> None:
    report = _build_llm_diagnostic(
        source_key="fc92d1710473",
        source_name="Credential (databricks)",
        source_type="CRD",
        source_id=132,
        project_name="integrations_exp_prd",
        target_id="70437463668053",
        target_name="Edge Server Testing",
        state_id=70437463668053,
        state_address='module.dbt_cloud.module.projects_v2[0].dbtcloud_environment.environments["integrations_exp_prd_edge_server_testing"]',
        state_resource_index="integrations_exp_prd_edge_server_testing",
        drift_status="in_sync",
        confidence="env_parent_match",
        action="match",
        is_protected=False,
        has_state_loaded=True,
        grid_row={
            "confidence": "env_parent_match",
            "status": "pending",
            "target_name": "Edge Server Testing",
            "target_id": "70437463668053",
        },
        source_data={"environment_name": "Edge Server Testing"},
        state_resource={"resource_index": "integrations_exp_prd_edge_server_testing"},
        app_state=None,
    )

    assert "- Match type: **crd_env_inherited**" in report
    assert "❌ Keys do NOT match" not in report
    assert "- **Parent ENV State Address**:" in report
    assert '2. **Parent environment fallback**: `target_env_by_proj_env_name[("integrations_exp_prd", "Edge Server Testing")]`' in report
    assert "3. **State ID lookup**: `target_by_id[70437463668053]` for type ENV" in report
