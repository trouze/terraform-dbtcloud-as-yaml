"""Tests for auto-dummy credential behavior on the target_credentials page.

Verifies that:
- Deployment environments without existing .env config auto-default to dummy mode
- Auto-dummy configs use build_dummy_credentials_from_source (source non-sensitive + dummy secrets)
- Development environments remain unaffected (no auto-dummy)
- Environments with existing .env config are not overridden
- Save All includes auto-dummy configs with source values preserved
- The save uses build_dummy_credentials_from_source, not get_dummy_credentials
"""

from unittest.mock import MagicMock, patch

import pytest

from importer.web.state import AppState, EnvironmentCredentialConfig
from importer.web.components.credential_schemas import (
    build_dummy_credentials_from_source,
    get_dummy_credentials,
    get_sensitive_fields,
)


def _make_state(project_path: str = "/tmp/test-proj") -> AppState:
    state = AppState()
    state.project_path = project_path
    return state


def _make_environments():
    """Return a list of environments: one dev, two deployment (databricks + snowflake)."""
    return [
        {
            "id": "dev_env",
            "name": "Development",
            "project_id": "proj_1",
            "project_name": "Analytics",
            "connection_type": "databricks",
            "env_type": "development",
            "deployment_type": "",
            "dbt_version": "1.6.0",
            "custom_branch": "",
            "source_values": {"schema": "dev_schema", "catalog": "main"},
        },
        {
            "id": "prod_env",
            "name": "Production",
            "project_id": "proj_1",
            "project_name": "Analytics",
            "connection_type": "databricks",
            "env_type": "deployment",
            "deployment_type": "production",
            "dbt_version": "1.6.0",
            "custom_branch": "",
            "source_values": {"schema": "prod_schema", "catalog": "analytics"},
        },
        {
            "id": "staging_env",
            "name": "Staging",
            "project_id": "proj_1",
            "project_name": "Analytics",
            "connection_type": "snowflake",
            "env_type": "deployment",
            "deployment_type": "staging",
            "dbt_version": "1.6.0",
            "custom_branch": "",
            "source_values": {
                "schema": "staging_schema",
                "user": "svc_user",
                "warehouse": "WH_STAGING",
                "role": "ANALYST",
                "auth_type": "password",
                "num_threads": 4,
            },
        },
    ]


class TestAutoDefaultDummyCredentials:
    """Deployment envs without existing .env config should auto-default to dummy mode."""

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_deployment_env_defaults_to_dummy_mode(self, mock_load, mock_resolve):
        """Deployment environments should have use_dummy_credentials=True when no .env config exists."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        prod_config = state.env_credentials.get_config("prod_env")
        assert prod_config is not None
        assert prod_config.use_dummy_credentials is True, (
            "Deployment env should auto-default to dummy mode"
        )

        staging_config = state.env_credentials.get_config("staging_env")
        assert staging_config is not None
        assert staging_config.use_dummy_credentials is True

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_development_env_does_not_default_to_dummy(self, mock_load, mock_resolve):
        """Development environments should NOT auto-default to dummy mode."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        dev_config = state.env_credentials.get_config("dev_env")
        assert dev_config is not None
        assert dev_config.use_dummy_credentials is False

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_auto_dummy_populates_credential_values_from_source(self, mock_load, mock_resolve):
        """Auto-dummy should pre-populate credential_values with source non-sensitive + dummy secrets."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        prod_config = state.env_credentials.get_config("prod_env")
        assert prod_config.credential_values, "Auto-dummy config should have credential_values populated"
        assert prod_config.credential_values.get("schema") == "prod_schema", (
            "Source non-sensitive values should be preserved"
        )
        assert prod_config.credential_values.get("catalog") == "analytics"

        # Sensitive fields should have dummy values
        databricks_sensitive = get_sensitive_fields("databricks")
        for field in databricks_sensitive:
            assert prod_config.credential_values.get(field), (
                f"Sensitive field '{field}' should have a dummy value"
            )

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_snowflake_auto_dummy_preserves_source_values(self, mock_load, mock_resolve):
        """Snowflake auto-dummy should preserve user, warehouse, role from source."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        staging_config = state.env_credentials.get_config("staging_env")
        creds = staging_config.credential_values
        assert creds.get("schema") == "staging_schema"
        assert creds.get("user") == "svc_user"
        assert creds.get("warehouse") == "WH_STAGING"
        assert creds.get("role") == "ANALYST"
        assert creds.get("auth_type") == "password"

        # Password should be a dummy placeholder
        assert "dummy" in creds.get("password", "").lower() or "placeholder" in creds.get("password", "").lower(), (
            "Snowflake password should be a dummy placeholder value"
        )

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch(
        "importer.web.pages.target_credentials.load_env_credential_configs",
        return_value={"prod_env": {"token": "real_token_123", "schema": "real_schema", "use_dummy": "false"}},
    )
    def test_existing_env_config_not_overridden(self, mock_load, mock_resolve):
        """Environments with existing .env config should keep their config, not be auto-dummied."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        prod_config = state.env_credentials.get_config("prod_env")
        assert prod_config.use_dummy_credentials is False, (
            "Existing .env config with use_dummy=false should not be overridden"
        )
        assert prod_config.credential_values.get("token") == "real_token_123"
        assert prod_config.is_saved is True

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_auto_dummy_is_not_saved_until_explicit_save(self, mock_load, mock_resolve):
        """Auto-dummy configs should have is_saved=False until Save All is clicked."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        prod_config = state.env_credentials.get_config("prod_env")
        assert prod_config.is_saved is False, (
            "Auto-dummy config should not be marked as saved until explicit save"
        )


class TestAutoUpgradeExistingConfigs:
    """Existing unsaved deployment env configs should be auto-upgraded to dummy mode."""

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_existing_unsaved_empty_config_upgraded_to_dummy(self, mock_load, mock_resolve):
        """A pre-existing config with empty credential_values and is_saved=False should be upgraded."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        # Pre-populate with an old-style empty config (simulating state restored from disk)
        old_config = EnvironmentCredentialConfig(
            env_id="prod_env",
            env_name="Production",
            project_id="proj_1",
            project_name="Analytics",
            connection_type="databricks",
            credential_type="databricks",
            env_type="deployment",
            deployment_type="production",
            credential_values={},
            source_values={"schema": "prod_schema", "catalog": "analytics"},
            use_dummy_credentials=False,
            is_saved=False,
        )
        state.env_credentials.set_config(old_config)

        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        config = state.env_credentials.get_config("prod_env")
        assert config.use_dummy_credentials is True, (
            "Existing unsaved empty config should be auto-upgraded to dummy"
        )
        assert config.credential_values, "Should have dummy credential values"
        assert config.credential_values.get("schema") == "prod_schema"

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value=None)
    @patch("importer.web.pages.target_credentials.load_env_credential_configs", return_value={})
    def test_existing_saved_config_not_upgraded(self, mock_load, mock_resolve):
        """A saved config should NOT be auto-upgraded even if it was manually configured."""
        from importer.web.pages.target_credentials import _initialize_env_configs

        state = _make_state()
        old_config = EnvironmentCredentialConfig(
            env_id="prod_env",
            env_name="Production",
            project_id="proj_1",
            project_name="Analytics",
            connection_type="databricks",
            credential_type="databricks",
            env_type="deployment",
            deployment_type="production",
            credential_values={"token": "real_token"},
            source_values={"schema": "prod_schema"},
            use_dummy_credentials=False,
            is_saved=True,
        )
        state.env_credentials.set_config(old_config)

        envs = _make_environments()
        save_state = MagicMock()

        _initialize_env_configs(state, envs, save_state)

        config = state.env_credentials.get_config("prod_env")
        assert config.use_dummy_credentials is False, (
            "Saved config should NOT be auto-upgraded"
        )
        assert config.credential_values.get("token") == "real_token"


class TestSaveAllWithAutoDummy:
    """Save All should include auto-dummy configs and use build_dummy_credentials_from_source."""

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value="/tmp/target.env")
    @patch("importer.web.pages.target_credentials.save_env_credential_config")
    @patch("importer.web.pages.target_credentials.ui")
    def test_save_all_includes_auto_dummy_envs(self, mock_ui, mock_save, mock_resolve):
        """Save All should save auto-dummy deployment environments."""
        from importer.web.pages.target_credentials import _save_all_configs

        state = _make_state()
        # Set up a deployment env with auto-dummy
        config = EnvironmentCredentialConfig(
            env_id="prod_env",
            env_name="Production",
            project_id="proj_1",
            project_name="Analytics",
            connection_type="databricks",
            credential_type="databricks",
            env_type="deployment",
            deployment_type="production",
            source_values={"schema": "prod_schema", "catalog": "analytics"},
            use_dummy_credentials=True,
            credential_values=build_dummy_credentials_from_source(
                "databricks", {"schema": "prod_schema", "catalog": "analytics"}
            ),
            is_saved=False,
        )
        state.env_credentials.set_config(config)
        state.env_credentials.selected_env_ids = {"prod_env"}

        save_state = MagicMock()
        _save_all_configs(state, save_state)

        mock_save.assert_called_once()
        saved_config = mock_save.call_args[1].get("config") or mock_save.call_args[0][1]
        assert saved_config.get("schema") == "prod_schema", (
            "Save All should preserve source non-sensitive values from build_dummy_credentials_from_source"
        )

    @patch("importer.web.pages.target_credentials.resolve_project_env_path", return_value="/tmp/target.env")
    @patch("importer.web.pages.target_credentials.save_env_credential_config")
    @patch("importer.web.pages.target_credentials.ui")
    def test_save_all_uses_source_aware_dummy(self, mock_ui, mock_save, mock_resolve):
        """Save All should use build_dummy_credentials_from_source (not just get_dummy_credentials)."""
        from importer.web.pages.target_credentials import _save_all_configs

        state = _make_state()
        config = EnvironmentCredentialConfig(
            env_id="staging_env",
            env_name="Staging",
            project_id="proj_1",
            project_name="Analytics",
            connection_type="snowflake",
            credential_type="snowflake",
            env_type="deployment",
            deployment_type="staging",
            source_values={
                "schema": "staging_schema",
                "user": "svc_user",
                "warehouse": "WH_STAGING",
                "role": "ANALYST",
                "auth_type": "password",
                "num_threads": 4,
            },
            use_dummy_credentials=True,
            credential_values=build_dummy_credentials_from_source(
                "snowflake",
                {
                    "schema": "staging_schema",
                    "user": "svc_user",
                    "warehouse": "WH_STAGING",
                    "role": "ANALYST",
                    "auth_type": "password",
                    "num_threads": 4,
                },
            ),
            is_saved=False,
        )
        state.env_credentials.set_config(config)
        state.env_credentials.selected_env_ids = {"staging_env"}

        save_state = MagicMock()
        _save_all_configs(state, save_state)

        mock_save.assert_called_once()
        saved_config = mock_save.call_args[1].get("config") or mock_save.call_args[0][1]

        assert saved_config.get("user") == "svc_user", (
            "Source non-sensitive 'user' should be preserved in saved dummy config"
        )
        assert saved_config.get("warehouse") == "WH_STAGING"
        assert saved_config.get("role") == "ANALYST"


class TestBuildDummyFromSourceContract:
    """Verify build_dummy_credentials_from_source produces valid TF-compatible credentials."""

    def test_databricks_dummy_has_token(self):
        result = build_dummy_credentials_from_source("databricks", {"schema": "my_schema", "catalog": "main"})
        assert result.get("schema") == "my_schema"
        assert result.get("catalog") == "main"
        assert result.get("token"), "Databricks dummy should have a token"
        assert result.get("credential_type") == "databricks"

    def test_snowflake_password_dummy_has_all_fields(self):
        source = {
            "schema": "analytics",
            "user": "admin",
            "warehouse": "WH_PROD",
            "role": "ADMIN",
            "auth_type": "password",
            "num_threads": 8,
        }
        result = build_dummy_credentials_from_source("snowflake", source)
        assert result.get("schema") == "analytics"
        assert result.get("user") == "admin"
        assert result.get("warehouse") == "WH_PROD"
        assert result.get("role") == "ADMIN"
        assert result.get("auth_type") == "password"
        assert result.get("password"), "Snowflake password auth should have dummy password"
        assert result.get("credential_type") == "snowflake"

    def test_snowflake_keypair_dummy_has_private_key(self):
        source = {
            "schema": "analytics",
            "user": "admin",
            "auth_type": "keypair",
        }
        result = build_dummy_credentials_from_source("snowflake", source)
        assert result.get("auth_type") == "keypair"
        assert result.get("private_key"), "Keypair auth should have dummy private key"
        assert "BEGIN PRIVATE KEY" in result["private_key"]

    def test_postgres_dummy_has_password(self):
        source = {"default_schema": "public", "username": "db_user", "num_threads": 4}
        result = build_dummy_credentials_from_source("postgres", source)
        assert result.get("default_schema") == "public"
        assert result.get("username") == "db_user"
        assert result.get("password"), "Postgres dummy should have a password"

    def test_empty_source_values_still_produces_dummy(self):
        result = build_dummy_credentials_from_source("databricks", {})
        assert result.get("token"), "Even with empty source, dummy should have required sensitive fields"
        assert result.get("credential_type") == "databricks"
