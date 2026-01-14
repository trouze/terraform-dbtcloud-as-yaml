"""Connection provider configuration component for the Target page."""

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import yaml
from nicegui import ui

from importer.web.env_manager import (
    load_connection_configs,
    save_connection_config,
    get_env_file_path,
)

# dbt brand colors
DBT_ORANGE = "#FF694A"
DBT_NAVY = "#192847"

# Connection type schemas - required fields, optional fields, and descriptions
# Based on dbtcloud_global_connection terraform provider resource schemas
CONNECTION_SCHEMAS = {
    "snowflake": {
        "required": ["account", "database", "warehouse"],
        "optional": [
            "role",
            "client_session_keep_alive",
            "allow_sso",
            "oauth_client_id",
            "oauth_client_secret",
        ],
        "sensitive": ["oauth_client_secret"],
        "oauth_fields": ["allow_sso", "oauth_client_id", "oauth_client_secret"],  # Fields to show under OAuth section
        "conditional": {
            # OAuth fields are required when allow_sso is enabled
            "oauth_client_id": {"depends_on": "allow_sso", "when": True},
            "oauth_client_secret": {"depends_on": "allow_sso", "when": True},
        },
        "descriptions": {
            "account": "Snowflake account identifier (e.g., 'abc12345.us-east-1')",
            "database": "Default database name",
            "warehouse": "Compute warehouse name",
            "role": "Default Snowflake role to use",
            "client_session_keep_alive": "Keep session alive for long queries (true/false)",
            "allow_sso": "Enable SSO/OAuth authentication (true/false)",
            "oauth_client_id": "OAuth Client ID (required when SSO is enabled)",
            "oauth_client_secret": "OAuth Client Secret (required when SSO is enabled)",
        },
    },
    "databricks": {
        "required": ["host", "http_path"],
        "optional": ["catalog", "client_id", "client_secret"],
        "sensitive": ["client_secret"],
        "oauth_fields": ["client_id", "client_secret"],  # Fields to show under OAuth section
        "descriptions": {
            "host": "Databricks workspace URL (e.g., 'workspace.cloud.databricks.com')",
            "http_path": "SQL warehouse HTTP path (e.g., '/sql/1.0/warehouses/abc123')",
            "catalog": "Unity Catalog name",
            "client_id": "OAuth Client ID for Databricks authentication",
            "client_secret": "OAuth Client Secret for Databricks authentication",
        },
    },
    "bigquery": {
        "required": ["gcp_project_id"],
        "optional": [
            "location",
            "timeout_seconds",
            "priority",
            # Auth type selector
            "deployment_env_auth_type",
            "use_latest_adapter",
            # Service Account JSON fields
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
            # External OAuth (WIF) fields
            "application_id",
            "application_secret",
            "scopes",
            # Query configuration
            "maximum_bytes_billed",
            "retries",
            "job_creation_timeout_seconds",
            "job_execution_timeout_seconds",
            "job_retry_deadline_seconds",
            # Execution options
            "execution_project",
            "impersonate_service_account",
            # Dataproc configuration
            "dataproc_region",
            "dataproc_cluster_name",
            "gcs_bucket",
        ],
        "sensitive": ["private_key", "application_secret"],
        # OAuth fields to show under OAuth section (auth type selector + WIF fields)
        "oauth_fields": ["deployment_env_auth_type", "application_id", "application_secret", "scopes"],
        "conditional": {
            # Service Account JSON fields shown when auth type is service-account-json
            "private_key_id": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "private_key": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "client_email": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "client_id": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "auth_uri": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "token_uri": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "auth_provider_x509_cert_url": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            "client_x509_cert_url": {"depends_on": "deployment_env_auth_type", "when": "service-account-json"},
            # External OAuth WIF fields shown when auth type is external-oauth-wif
            "application_id": {"depends_on": "deployment_env_auth_type", "when": "external-oauth-wif"},
            "application_secret": {"depends_on": "deployment_env_auth_type", "when": "external-oauth-wif"},
            "scopes": {"depends_on": "deployment_env_auth_type", "when": "external-oauth-wif"},
        },
        "select_options": {
            "deployment_env_auth_type": ["service-account-json", "external-oauth-wif"],
            "priority": ["INTERACTIVE", "BATCH"],
        },
        "descriptions": {
            "gcp_project_id": "GCP project ID for the BigQuery connection",
            "location": "Dataset location (e.g., 'US', 'EU')",
            "timeout_seconds": "Query timeout in seconds (for bigquery_v0 adapter)",
            "priority": "Query priority: 'INTERACTIVE' or 'BATCH'",
            "deployment_env_auth_type": "Auth type: 'service-account-json' or 'external-oauth-wif'",
            "use_latest_adapter": "Use bigquery_v1 adapter (required for WIF)",
            # Service Account JSON
            "private_key_id": "Private Key ID from service account JSON",
            "private_key": "Private Key from service account JSON",
            "client_email": "Service Account email",
            "client_id": "Client ID from service account JSON",
            "auth_uri": "Auth URI (typically 'https://accounts.google.com/o/oauth2/auth')",
            "token_uri": "Token URI (typically 'https://oauth2.googleapis.com/token')",
            "auth_provider_x509_cert_url": "Auth Provider X509 Cert URL",
            "client_x509_cert_url": "Client X509 Cert URL",
            # External OAuth WIF
            "application_id": "OAuth Application/Client ID (for Workload Identity Federation)",
            "application_secret": "OAuth Application/Client Secret (for WIF)",
            "scopes": "OAuth scopes (comma-separated)",
            # Query configuration
            "maximum_bytes_billed": "Max bytes that can be billed per query",
            "retries": "Number of retries for queries",
            "job_creation_timeout_seconds": "Max timeout for job creation step",
            "job_execution_timeout_seconds": "Timeout for job execution (bigquery_v1)",
            "job_retry_deadline_seconds": "Total seconds to wait while retrying",
            # Execution options
            "execution_project": "Project to bill for query execution",
            "impersonate_service_account": "Service Account to impersonate",
            # Dataproc configuration
            "dataproc_region": "Google Cloud region for PySpark on Dataproc",
            "dataproc_cluster_name": "Dataproc cluster name for PySpark workloads",
            "gcs_bucket": "GCS bucket URI for Python code via Dataproc",
        },
    },
    "redshift": {
        "required": ["hostname", "port", "dbname"],
        "optional": [
            # SSH Tunnel configuration
            "ssh_tunnel_enabled",
            "ssh_tunnel_hostname",
            "ssh_tunnel_port",
            "ssh_tunnel_username",
        ],
        "sensitive": ["password"],
        "conditional": {
            # SSH tunnel fields shown when ssh_tunnel_enabled is true
            "ssh_tunnel_hostname": {"depends_on": "ssh_tunnel_enabled", "when": True},
            "ssh_tunnel_port": {"depends_on": "ssh_tunnel_enabled", "when": True},
            "ssh_tunnel_username": {"depends_on": "ssh_tunnel_enabled", "when": True},
        },
        "descriptions": {
            "hostname": "Redshift cluster endpoint",
            "port": "Port number (default: 5439)",
            "dbname": "Database name",
            "ssh_tunnel_enabled": "Enable SSH tunnel for connection (true/false)",
            "ssh_tunnel_hostname": "SSH tunnel hostname",
            "ssh_tunnel_port": "SSH tunnel port",
            "ssh_tunnel_username": "SSH tunnel username",
            # Note: External OAuth for Redshift is documented but limited in terraform provider
        },
    },
    "postgres": {
        "required": ["hostname", "port", "dbname"],
        "optional": [
            "ssh_tunnel_enabled",
            "ssh_tunnel_hostname",
            "ssh_tunnel_port",
            "ssh_tunnel_username",
        ],
        "sensitive": ["password"],
        "conditional": {
            "ssh_tunnel_hostname": {"depends_on": "ssh_tunnel_enabled", "when": True},
            "ssh_tunnel_port": {"depends_on": "ssh_tunnel_enabled", "when": True},
            "ssh_tunnel_username": {"depends_on": "ssh_tunnel_enabled", "when": True},
        },
        "descriptions": {
            "hostname": "PostgreSQL hostname",
            "port": "Port number (default: 5432)",
            "dbname": "Database name",
            "ssh_tunnel_enabled": "Enable SSH tunnel for connection (true/false)",
            "ssh_tunnel_hostname": "SSH tunnel hostname",
            "ssh_tunnel_port": "SSH tunnel port",
            "ssh_tunnel_username": "SSH tunnel username",
        },
    },
    "athena": {
        "required": ["region_name", "database", "s3_staging_dir"],
        "optional": [
            "work_group",
            "s3_data_dir",
            "s3_tmp_table_dir",
            "s3_data_naming",
            "num_retries",
            "num_boto3_retries",
            "num_iceberg_retries",
            "poll_interval",
            "spark_work_group",
        ],
        "sensitive": [],
        "descriptions": {
            "region_name": "AWS region (e.g., 'us-east-1')",
            "database": "Athena database name (data catalog)",
            "s3_staging_dir": "S3 staging directory (e.g., 's3://bucket/staging/')",
            "work_group": "Athena workgroup identifier",
            "s3_data_dir": "S3 data directory prefix",
            "s3_tmp_table_dir": "S3 temp table directory prefix",
            "s3_data_naming": "How to generate table paths in S3",
            "num_retries": "Number of query retries",
            "num_boto3_retries": "Number of boto3 request retries",
            "num_iceberg_retries": "Number of Iceberg commit retries",
            "poll_interval": "Polling interval in seconds",
            "spark_work_group": "Athena Spark workgroup for Python models",
        },
    },
    "fabric": {
        "required": ["server", "database"],
        "optional": ["port", "retries", "login_timeout", "query_timeout"],
        "sensitive": [],
        "descriptions": {
            "server": "Microsoft Fabric server hostname",
            "database": "Database name",
            "port": "Port number (default: 1433)",
            "retries": "Number of automatic query retries",
            "login_timeout": "Login timeout in seconds",
            "query_timeout": "Query timeout in seconds",
        },
    },
    "synapse": {
        "required": ["host", "database"],
        "optional": ["port", "retries", "login_timeout", "query_timeout"],
        "sensitive": [],
        "descriptions": {
            "host": "Azure Synapse Analytics hostname",
            "database": "Database name",
            "port": "Port number (default: 1433)",
            "retries": "Number of automatic query retries",
            "login_timeout": "Login timeout in seconds",
            "query_timeout": "Query timeout in seconds",
        },
    },
    "starburst": {
        "required": ["host"],
        "optional": ["port", "method"],
        "sensitive": [],
        "descriptions": {
            "host": "Starburst/Trino hostname",
            "port": "Port number (default: 443)",
            "method": "Authentication method (e.g., 'LDAP')",
        },
    },
    "apache_spark": {
        "required": ["host", "method", "cluster"],
        "optional": ["port", "organization", "user", "auth", "connect_timeout", "connect_retries"],
        "sensitive": [],
        "descriptions": {
            "host": "Spark cluster hostname",
            "method": "Authentication method ('http' or 'thrift')",
            "cluster": "Spark cluster name",
            "port": "Port number (default: 443)",
            "organization": "Organization ID",
            "user": "Username",
            "auth": "Auth token",
            "connect_timeout": "Connection timeout in seconds",
            "connect_retries": "Number of connection retries",
        },
    },
    "teradata": {
        "required": ["host", "tmode"],
        "optional": ["port", "retries", "request_timeout"],
        "sensitive": [],
        "descriptions": {
            "host": "Teradata hostname",
            "tmode": "Transaction mode (e.g., 'ANSI')",
            "port": "Port number (default: 1025)",
            "retries": "Number of query retries",
            "request_timeout": "Request timeout in seconds",
        },
    },
}


def get_schema_for_connection_type(conn_type: str) -> Optional[Dict]:
    """Get the schema for a given connection type.
    
    Args:
        conn_type: Connection type string (e.g., 'snowflake', 'databricks')
        
    Returns:
        Schema dict or None if not found
    """
    conn_type_lower = conn_type.lower()
    for schema_type, schema_data in CONNECTION_SCHEMAS.items():
        if schema_type in conn_type_lower:
            return schema_data
    return None


def load_connections_from_yaml(yaml_path: str) -> List[Dict[str, Any]]:
    """Load connections from a normalized YAML file.
    
    Args:
        yaml_path: Path to the normalized YAML file
        
    Returns:
        List of connection dictionaries
    """
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("globals", {}).get("connections", [])
    except Exception:
        return []


def create_connection_config_section(
    yaml_path: Optional[str],
    on_config_change: Optional[Callable[[], None]] = None,
) -> None:
    """Create the connection configuration section.
    
    This creates a card with collapsible sections for each connection,
    allowing users to configure provider-specific details.
    
    Args:
        yaml_path: Path to the normalized YAML file
        on_config_change: Callback when configuration changes
    """
    if not yaml_path or not Path(yaml_path).exists():
        _create_no_yaml_warning()
        return
    
    connections = load_connections_from_yaml(yaml_path)
    if not connections:
        _create_no_connections_info()
        return
    
    # Load existing configs from .env
    existing_configs = load_connection_configs()
    
    # Store form data
    connection_forms: Dict[str, Dict[str, Any]] = {}
    
    with ui.card().classes("w-full"):
        with ui.row().classes("items-center justify-between mb-4"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("cable", size="md").style(f"color: {DBT_ORANGE};")
                ui.label("Connection Provider Config").classes("text-lg font-semibold")
            
            # Save all button
            ui.button(
                "Save All to .env",
                icon="save",
                on_click=lambda: _save_all_configs(connections, connection_forms),
            ).props("outline size=sm")
        
        ui.label(
            "Configure connection provider details for deployment. "
            "These will be saved as environment variables."
        ).classes("text-sm text-slate-600 dark:text-slate-400 mb-4")
        
        # Note about data sources
        with ui.row().classes("items-center gap-2 p-2 bg-blue-50 dark:bg-blue-900/20 rounded mb-4"):
            ui.icon("info", size="sm").classes("text-blue-500")
            ui.label(
                "Non-sensitive fields (host, account, etc.) are pre-filled from the API. "
                "Sensitive credentials must be entered manually or loaded from .env."
            ).classes("text-xs text-blue-600 dark:text-blue-400")
        
        # Create collapsible section for each connection
        for conn in connections:
            conn_key = conn.get("key", "unknown")
            conn_name = conn.get("name", conn_key)
            conn_type = conn.get("type", "unknown")
            
            # Initialize form data with existing config or empty dict
            existing = existing_configs.get(conn_key, {})
            connection_forms[conn_key] = dict(existing)
            
            _create_connection_form(
                conn_key=conn_key,
                conn_name=conn_name,
                conn_type=conn_type,
                existing_config=existing,
                form_data=connection_forms[conn_key],
                conn_details=conn,  # Pass full connection data for view button
                on_config_change=on_config_change,
            )


def _create_no_yaml_warning() -> None:
    """Show warning when no YAML file is available."""
    with ui.card().classes("w-full bg-yellow-50 dark:bg-yellow-900/20"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("warning", size="md").classes("text-yellow-500")
            with ui.column().classes("gap-1"):
                ui.label("No Migration Config Found").classes(
                    "font-medium text-yellow-700 dark:text-yellow-400"
                )
                ui.label(
                    "Complete the Map step to generate a normalized YAML file first."
                ).classes("text-sm text-yellow-600 dark:text-yellow-500")


def _create_no_connections_info() -> None:
    """Show info when YAML has no connections."""
    with ui.card().classes("w-full bg-slate-50 dark:bg-slate-800/50"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("info", size="md").classes("text-slate-400")
            with ui.column().classes("gap-1"):
                ui.label("No Connections to Configure").classes(
                    "font-medium text-slate-600 dark:text-slate-400"
                )
                ui.label(
                    "The migration configuration doesn't include any connections."
                ).classes("text-sm text-slate-500")


def _create_connection_form(
    conn_key: str,
    conn_name: str,
    conn_type: str,
    existing_config: Dict[str, Any],
    form_data: Dict[str, Any],
    conn_details: Optional[Dict[str, Any]] = None,
    on_config_change: Optional[Callable[[], None]] = None,
) -> None:
    """Create a collapsible form for a single connection.
    
    Args:
        conn_key: Connection key identifier
        conn_name: Display name for the connection
        conn_type: Connection type (snowflake, databricks, etc.)
        existing_config: Existing configuration from .env
        form_data: Dictionary to store form values
        conn_details: Full connection details from fetched data
        on_config_change: Callback when form values change
    """
    schema = get_schema_for_connection_type(conn_type)
    
    # Merge provider_config from API (if available) with existing .env config
    # .env values take precedence over API-fetched values
    provider_config = conn_details.get("provider_config", {}) if conn_details else {}
    merged_config = {**provider_config, **existing_config}  # .env overrides provider_config
    
    has_config = bool(merged_config)
    has_env_config = bool(existing_config)
    has_api_config = bool(provider_config)
    
    # Track conditional field containers for visibility updates
    conditional_containers: Dict[str, ui.element] = {}
    
    def update_conditional_visibility(changed_field: str, new_value: Any):
        """Update visibility of conditional fields when a dependency changes."""
        conditionals = schema.get("conditional", {})
        for field, condition in conditionals.items():
            if condition.get("depends_on") == changed_field:
                container = conditional_containers.get(field)
                if container:
                    expected_value = condition.get("when")
                    # Handle boolean comparison
                    if isinstance(expected_value, bool):
                        should_show = bool(new_value) == expected_value
                    else:
                        should_show = str(new_value) == str(expected_value)
                    container.set_visibility(should_show)
    
    def should_show_field(field: str) -> bool:
        """Determine if a conditional field should be initially visible."""
        conditionals = schema.get("conditional", {})
        if field not in conditionals:
            return True  # Non-conditional fields are always shown
        
        condition = conditionals[field]
        depends_on = condition.get("depends_on")
        expected_value = condition.get("when")
        
        # Get current value of the dependency field
        current_value = merged_config.get(depends_on, form_data.get(depends_on, ""))
        
        # Handle boolean comparison
        if isinstance(expected_value, bool):
            if isinstance(current_value, bool):
                return current_value == expected_value
            return str(current_value).lower() == str(expected_value).lower()
        
        return str(current_value) == str(expected_value)
    
    with ui.expansion(
        text=f"{conn_name}",
        icon="storage",
        value=not has_config,  # Expand if no config yet
    ).classes("w-full mb-2") as expansion:
        # Connection type badge and view button
        with ui.row().classes("items-center gap-2 mb-3"):
            ui.badge(conn_type.upper(), color="primary").props("outline")
            ui.label(f"Key: {conn_key}").classes("text-xs text-slate-500 font-mono")
            if has_env_config:
                ui.badge("Saved to .env", color="green").props("outline")
            elif has_api_config:
                ui.badge("From API", color="blue").props("outline")
            
            # View details button - prominent labeled button for visibility
            ui.button(
                "View Details",
                icon="visibility",
                on_click=lambda cd=conn_details, cn=conn_name, ct=conn_type: _show_connection_detail_dialog(cd, cn, ct),
            ).props("outline size=sm color=primary")
        
        if not schema:
            # Unknown connection type
            with ui.row().classes("items-center gap-2 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded"):
                ui.icon("help", size="sm").classes("text-yellow-500")
                ui.label(
                    f"Unknown connection type '{conn_type}'. Configure manually if needed."
                ).classes("text-sm text-yellow-600 dark:text-yellow-500")
            return
        
        # Get schema properties
        select_options = schema.get("select_options", {})
        conditionals = schema.get("conditional", {})
        
        # Required fields
        if schema["required"]:
            ui.label("Required Fields").classes("text-sm font-medium text-slate-600 dark:text-slate-400 mb-2")
            with ui.column().classes("gap-2 mb-4"):
                for field in schema["required"]:
                    description = schema["descriptions"].get(field, field.replace("_", " ").title())
                    is_sensitive = field in schema.get("sensitive", [])
                    default_value = merged_config.get(field, "")
                    from_api = field in provider_config and field not in existing_config
                    field_select_options = select_options.get(field)
                    
                    # Store initial value
                    form_data[field] = default_value
                    
                    _create_form_field(
                        field=field,
                        description=description,
                        default_value=str(default_value) if default_value else "",
                        is_sensitive=is_sensitive,
                        is_required=True,
                        form_data=form_data,
                        conn_type=conn_type,
                        from_api=from_api,
                        select_options=field_select_options,
                        on_change_callback=update_conditional_visibility,
                    )
        
        # OAuth documentation URLs for supported providers
        # Some providers have multiple OAuth options (e.g., Snowflake has SSO OAuth and External OAuth)
        oauth_docs_urls = {
            "snowflake": [
                ("Snowflake SSO OAuth setup guide", "https://docs.getdbt.com/docs/cloud/manage-access/set-up-snowflake-oauth"),
                ("Snowflake External OAuth setup guide (Okta/Entra ID)", "https://docs.getdbt.com/docs/cloud/manage-access/snowflake-external-oauth"),
            ],
            "databricks": [
                ("Databricks OAuth setup guide", "https://docs.getdbt.com/docs/cloud/manage-access/set-up-databricks-oauth"),
            ],
            "bigquery": [
                ("BigQuery OAuth setup guide", "https://docs.getdbt.com/docs/cloud/manage-access/set-up-bigquery-oauth"),
            ],
        }
        
        # Get OAuth fields defined for this connection type
        oauth_fields_list = schema.get("oauth_fields", [])
        
        # Optional fields - separate OAuth fields, conditional fields, and regular optional fields
        if schema["optional"]:
            # Categorize optional fields:
            # - oauth_fields: Fields that belong under OAuth section
            # - conditional_fields: Fields with visibility conditions (not already in oauth)
            # - regular_optional: Everything else
            oauth_optional_fields = [f for f in schema["optional"] if f in oauth_fields_list]
            conditional_fields = [f for f in schema["optional"] if f in conditionals and f not in oauth_fields_list]
            regular_optional_fields = [f for f in schema["optional"] if f not in oauth_fields_list and f not in conditionals]
            
            # Render regular optional fields under "Optional Fields"
            if regular_optional_fields:
                ui.label("Optional Fields").classes("text-sm font-medium text-slate-600 dark:text-slate-400 mb-2 mt-4")
                with ui.column().classes("gap-2"):
                    for field in regular_optional_fields:
                        description = schema["descriptions"].get(field, field.replace("_", " ").title())
                        is_sensitive = field in schema.get("sensitive", [])
                        default_value = merged_config.get(field, "")
                        from_api = field in provider_config and field not in existing_config
                        field_select_options = select_options.get(field)
                        
                        if default_value:
                            form_data[field] = default_value
                        
                        _create_form_field(
                            field=field,
                            description=description,
                            default_value=str(default_value) if default_value else "",
                            is_sensitive=is_sensitive,
                            is_required=False,
                            form_data=form_data,
                            conn_type=conn_type,
                            from_api=from_api,
                            select_options=field_select_options,
                            on_change_callback=update_conditional_visibility,
                        )
            
            # Show OAuth section for ALL connections that support OAuth
            # regardless of whether source has SSO configured
            docs_links = oauth_docs_urls.get(conn_type)
            if docs_links:
                ui.label("OAuth / SSO Configuration").classes(
                    "text-sm font-medium text-slate-600 dark:text-slate-400 mb-2 mt-4"
                )
                
                # Warning card about OAuth integrations
                with ui.card().classes("w-full bg-amber-50 dark:bg-amber-900/20 border-l-4 border-amber-400 p-3 mb-3"):
                    with ui.row().classes("items-start gap-2"):
                        ui.icon("warning", size="sm").classes("text-amber-600 dark:text-amber-400 mt-0.5")
                        with ui.column().classes("gap-1"):
                            ui.label("OAuth integrations cannot be reused from source").classes(
                                "text-sm font-medium text-amber-800 dark:text-amber-200"
                            )
                            ui.label(
                                "The callback URL differs between accounts. You must create a new OAuth "
                                "security integration in the target account."
                            ).classes("text-xs text-amber-700 dark:text-amber-300")
                            # Show all documentation links for this provider
                            for link_text, link_url in docs_links:
                                ui.link(
                                    f"{link_text} →",
                                    link_url,
                                    new_tab=True,
                                ).classes("text-xs text-amber-600 dark:text-amber-400 hover:underline")
                
                # Render OAuth fields (may have conditional visibility)
                with ui.column().classes("gap-2"):
                    for field in oauth_optional_fields:
                        description = schema["descriptions"].get(field, field.replace("_", " ").title())
                        is_sensitive = field in schema.get("sensitive", [])
                        default_value = merged_config.get(field, "")
                        from_api = field in provider_config and field not in existing_config
                        field_select_options = select_options.get(field)
                        
                        if default_value:
                            form_data[field] = default_value
                        
                        # Check if this field has conditional visibility
                        if field in conditionals:
                            initial_visible = should_show_field(field)
                            container = ui.column().classes("w-full")
                            container.set_visibility(initial_visible)
                            conditional_containers[field] = container
                            
                            with container:
                                _create_form_field(
                                    field=field,
                                    description=description,
                                    default_value=str(default_value) if default_value else "",
                                    is_sensitive=is_sensitive,
                                    is_required=False,
                                    form_data=form_data,
                                    conn_type=conn_type,
                                    from_api=from_api,
                                    select_options=field_select_options,
                                    on_change_callback=update_conditional_visibility,
                                )
                        else:
                            _create_form_field(
                                field=field,
                                description=description,
                                default_value=str(default_value) if default_value else "",
                                is_sensitive=is_sensitive,
                                is_required=False,
                                form_data=form_data,
                                conn_type=conn_type,
                                from_api=from_api,
                                select_options=field_select_options,
                                on_change_callback=update_conditional_visibility,
                            )
            
            # Render any remaining conditional fields (e.g., SSH tunnel fields, service account fields)
            if conditional_fields:
                with ui.column().classes("gap-2 mt-4"):
                    for field in conditional_fields:
                        description = schema["descriptions"].get(field, field.replace("_", " ").title())
                        is_sensitive = field in schema.get("sensitive", [])
                        default_value = merged_config.get(field, "")
                        from_api = field in provider_config and field not in existing_config
                        field_select_options = select_options.get(field)
                        
                        if default_value:
                            form_data[field] = default_value
                        
                        # Wrap in a container for visibility control
                        initial_visible = should_show_field(field)
                        container = ui.column().classes("w-full")
                        container.set_visibility(initial_visible)
                        conditional_containers[field] = container
                        
                        with container:
                            _create_form_field(
                                field=field,
                                description=description,
                                default_value=str(default_value) if default_value else "",
                                is_sensitive=is_sensitive,
                                is_required=False,
                                form_data=form_data,
                                conn_type=conn_type,
                                from_api=from_api,
                                select_options=field_select_options,
                                on_change_callback=update_conditional_visibility,
                            )
        
        # Save button for this connection
        with ui.row().classes("justify-end mt-4"):
            ui.button(
                "Save to .env",
                icon="save",
                on_click=lambda ck=conn_key, fd=form_data: _save_single_config(ck, fd),
            ).props("outline size=sm")


def _create_form_field(
    field: str,
    description: str,
    default_value: str,
    is_sensitive: bool,
    is_required: bool,
    form_data: Dict[str, Any],
    conn_type: str,
    from_api: bool = False,
    select_options: Optional[List[str]] = None,
    on_change_callback: Optional[Callable[[str, Any], None]] = None,
) -> None:
    """Create a single form field.
    
    Args:
        field: Field name
        description: Field description/label
        default_value: Default value
        is_sensitive: Whether to mask the field
        is_required: Whether the field is required
        form_data: Dictionary to store the value
        conn_type: Connection type for smart defaults
        from_api: Whether this value came from the API fetch
        select_options: List of options for select/dropdown fields
        on_change_callback: Callback when field value changes (for conditional updates)
    """
    # Determine field type and create appropriate input
    # Boolean fields that should render as toggles
    boolean_fields = [
        "client_session_keep_alive", "allow_sso", "ssh_tunnel_enabled",
        "use_latest_adapter"
    ]
    is_boolean = field in boolean_fields
    is_port = field in ["port", "ssh_tunnel_port"]
    is_select = select_options is not None and len(select_options) > 0
    is_number = field in [
        "timeout_seconds", "num_retries", "num_boto3_retries", "num_iceberg_retries",
        "poll_interval", "maximum_bytes_billed", "retries", "connect_timeout",
        "connect_retries", "login_timeout", "query_timeout", "request_timeout",
    ]
    
    # Use short label from field name, put long description in tooltip
    label_text = field.replace("_", " ").title()
    if is_required:
        label_text += " *"
    
    # Add tooltip with description and source info
    tooltip_text = description
    if from_api and default_value:
        tooltip_text += " (pre-filled from API)"
    
    def handle_change(e, f=field):
        value = e.args
        _update_form_data(form_data, f, value)
        if on_change_callback:
            on_change_callback(f, value)
    
    with ui.row().classes("w-full items-start gap-3"):
        if is_boolean:
            # Boolean toggle
            initial = str(default_value).lower() == "true" if default_value else False
            form_data[field] = initial
            
            ui.label(label_text).classes("w-32 min-w-32 text-sm pt-1").tooltip(tooltip_text)
            switch = ui.switch(value=initial).props("dense")
            switch.on("update:model-value", handle_change)
            if from_api and default_value:
                ui.icon("cloud_done", size="xs").classes("text-blue-500").tooltip("From API")
        elif is_select:
            # Select/dropdown field
            form_data[field] = default_value or (select_options[0] if select_options else "")
            
            ui.label(label_text).classes("w-32 min-w-32 text-sm pt-2").tooltip(tooltip_text)
            select = ui.select(
                options=select_options,
                value=default_value or select_options[0],
            ).props("dense outlined").classes("flex-grow min-w-[300px]")
            select.on("update:model-value", handle_change)
            if from_api and default_value:
                ui.icon("cloud_done", size="xs").classes("text-blue-500").tooltip("From API")
        elif is_port or is_number:
            # Numeric field
            smart_default = default_value
            if not smart_default and is_port:
                if "postgres" in conn_type:
                    smart_default = "5432"
                elif "redshift" in conn_type:
                    smart_default = "5439"
                elif field == "ssh_tunnel_port":
                    smart_default = "22"
            
            form_data[field] = smart_default
            
            ui.label(label_text).classes("w-32 min-w-32 text-sm pt-2").tooltip(tooltip_text)
            input_field = ui.input(
                value=smart_default,
                placeholder="Enter number",
            ).props("dense outlined type=number").classes("flex-grow min-w-[300px]")
            input_field.on("update:model-value", handle_change)
            if from_api and default_value:
                ui.icon("cloud_done", size="xs").classes("text-blue-500").tooltip("From API")
        elif is_sensitive:
            # Password field
            form_data[field] = default_value
            
            ui.label(label_text).classes("w-32 min-w-32 text-sm pt-2").tooltip(tooltip_text)
            input_field = ui.input(
                value=default_value,
                password=True,
                password_toggle_button=True,
                placeholder="••••••••" if default_value else "",
            ).props("dense outlined").classes("flex-grow min-w-[300px]")
            input_field.on("update:model-value", handle_change)
        else:
            # Regular text field
            form_data[field] = default_value
            
            ui.label(label_text).classes("w-32 min-w-32 text-sm pt-2").tooltip(tooltip_text)
            input_field = ui.input(
                value=default_value,
                placeholder=description,
            ).props("dense outlined").classes("flex-grow min-w-[300px]")
            input_field.on("update:model-value", handle_change)
            if from_api and default_value:
                ui.icon("cloud_done", size="xs").classes("text-blue-500").tooltip("From API")


def _update_form_data(form_data: Dict[str, Any], field: str, value: Any) -> None:
    """Update form data when a field changes.
    
    Args:
        form_data: Dictionary to update
        field: Field name
        value: New value
    """
    form_data[field] = value


def _show_connection_detail_dialog(
    conn_details: Optional[Dict[str, Any]],
    conn_name: str,
    conn_type: str,
) -> None:
    """Show a dialog with connection details from the fetched data.
    
    Args:
        conn_details: Full connection data from fetch
        conn_name: Connection display name
        conn_type: Connection type
    """
    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl"):
        # Header
        with ui.row().classes("w-full items-center justify-between p-4 border-b"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("cable").style(f"color: {DBT_ORANGE};")
                ui.label(conn_name).classes("text-xl font-bold")
                ui.badge(conn_type.upper(), color="primary").props("outline")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense")
        
        with ui.column().classes("w-full p-4 gap-4"):
            if not conn_details:
                ui.label("No connection details available.").classes("text-slate-500")
            else:
                # Key info
                with ui.row().classes("gap-4 flex-wrap"):
                    if conn_details.get("key"):
                        with ui.column().classes("gap-0"):
                            ui.label("Key").classes("text-xs text-slate-500")
                            ui.label(conn_details["key"]).classes("font-mono text-sm")
                    if conn_details.get("id"):
                        with ui.column().classes("gap-0"):
                            ui.label("ID").classes("text-xs text-slate-500")
                            ui.label(str(conn_details["id"])).classes("font-mono text-sm")
                
                # Details section
                details = conn_details.get("details", {})
                if details:
                    ui.separator()
                    ui.label("API Details").classes("font-semibold")
                    
                    # Show key details in a grid
                    with ui.grid(columns=2).classes("w-full gap-2"):
                        for key, value in sorted(details.items()):
                            if value is not None and key not in ["config"]:
                                ui.label(key.replace("_", " ").title()).classes("text-xs text-slate-500")
                                display_val = str(value)
                                if len(display_val) > 50:
                                    display_val = display_val[:47] + "..."
                                ui.label(display_val).classes("text-sm font-mono truncate")
                
                # Note about missing data
                ui.separator()
                with ui.row().classes("items-center gap-2 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded"):
                    ui.icon("info", size="sm").classes("text-yellow-500")
                    ui.label(
                        "Provider-specific config (host, credentials, paths) is not returned by the dbt Cloud API "
                        "for security reasons. You must enter these values manually."
                    ).classes("text-xs text-yellow-600 dark:text-yellow-400")
                
                # JSON view
                ui.separator()
                with ui.expansion("View JSON", icon="code").classes("w-full"):
                    formatted_json = json.dumps(conn_details, indent=2, sort_keys=True)
                    with ui.row().classes("w-full justify-end"):
                        ui.button(
                            "Copy",
                            icon="content_copy",
                            on_click=lambda fj=formatted_json: (
                                ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(fj)})"),
                                ui.notify("Copied to clipboard", type="positive"),
                            ),
                        ).props("flat dense size=sm")
                    ui.code(formatted_json, language="json").classes("w-full text-xs")
    
    dialog.open()


def _save_single_config(conn_key: str, form_data: Dict[str, Any]) -> None:
    """Save a single connection configuration to .env.
    
    Args:
        conn_key: Connection key
        form_data: Form data to save
    """
    # Filter out empty values
    config = {k: v for k, v in form_data.items() if v is not None and v != ""}
    
    if not config:
        ui.notify(f"No configuration to save for {conn_key}", type="warning")
        return
    
    try:
        path = save_connection_config(conn_key, config)
        ui.notify(f"Saved {conn_key} config to {path}", type="positive")
    except Exception as e:
        ui.notify(f"Failed to save config: {e}", type="negative")


def _save_all_configs(
    connections: List[Dict[str, Any]],
    connection_forms: Dict[str, Dict[str, Any]],
) -> None:
    """Save all connection configurations to .env.
    
    Args:
        connections: List of connection dictionaries
        connection_forms: Dictionary of form data per connection
    """
    saved_count = 0
    
    for conn in connections:
        conn_key = conn.get("key")
        if not conn_key or conn_key not in connection_forms:
            continue
        
        form_data = connection_forms[conn_key]
        # Filter out empty values
        config = {k: v for k, v in form_data.items() if v is not None and v != ""}
        
        if config:
            try:
                save_connection_config(conn_key, config)
                saved_count += 1
            except Exception as e:
                ui.notify(f"Failed to save {conn_key}: {e}", type="negative")
    
    if saved_count > 0:
        env_path = get_env_file_path()
        ui.notify(f"Saved {saved_count} connection config(s) to {env_path}", type="positive")
    else:
        ui.notify("No configurations to save", type="warning")
