"""Tests for connection provider config backfill in UI forms."""

from importer.web.components.connection_config import _build_provider_config


def test_build_provider_config_backfills_private_key_id_from_details_config() -> None:
    """Backfill missing fields from details.config when provider_config is incomplete."""
    conn_details = {
        "provider_config": {
            "gcp_project_id": "ps-sthibeault-fusion-dev",
            "deployment_env_auth_type": "service-account-json",
            "client_email": "dbt-service@ps-sthibeault-fusion-dev.iam.gserviceaccount.com",
        },
        "details": {
            "config": {
                "project_id": "ps-sthibeault-fusion-dev",
                "private_key_id": "8efdff6229f48bfc1047e7259e8d0d968ef55a78",
                "client_id": "110206344724199657711",
            }
        },
    }

    result = _build_provider_config(conn_details)
    assert result["gcp_project_id"] == "ps-sthibeault-fusion-dev"
    assert result["private_key_id"] == "8efdff6229f48bfc1047e7259e8d0d968ef55a78"
    assert result["client_id"] == "110206344724199657711"


def test_build_provider_config_maps_project_id_when_provider_missing_gcp_project_id() -> None:
    """Map details.config.project_id -> gcp_project_id for BigQuery form prefill."""
    conn_details = {
        "provider_config": {},
        "details": {"config": {"project_id": "ps-sthibeault-fusion-dev"}},
    }

    result = _build_provider_config(conn_details)
    assert result["project_id"] == "ps-sthibeault-fusion-dev"
    assert result["gcp_project_id"] == "ps-sthibeault-fusion-dev"
