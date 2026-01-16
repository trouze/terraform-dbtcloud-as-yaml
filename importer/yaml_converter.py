"""YAML to Terraform deployment setup.

This module creates a Terraform deployment directory that uses the 
terraform-dbtcloud-yaml module to deploy dbt Cloud resources from 
a normalized YAML configuration file.

Follows the same pattern as test/e2e_test/ - generates main.tf that
references the root module, and relies on TF_VAR_* environment 
variables for credentials (not stored in files).
"""

import shutil
from pathlib import Path
from typing import Dict, Optional, Any

import yaml


# Sensitive credential fields that should be included in connection_credentials
# These are the fields that need to be passed via TF_VAR for security
SENSITIVE_CONNECTION_FIELDS = {
    # Snowflake OAuth
    "oauth_client_id",
    "oauth_client_secret",
    # Databricks OAuth
    "client_id",
    "client_secret",
    # BigQuery Service Account
    "private_key_id",
    "private_key",
    # BigQuery External OAuth (WIF)
    "application_id",
    "application_secret",
}


class YamlToTerraformConverter:
    """Sets up a Terraform deployment directory for deploying dbt Cloud resources."""

    def __init__(
        self,
        module_source: Optional[str] = None,
        provider_version: str = "= 1.5.1",
    ):
        """Initialize the converter.

        Args:
            module_source: Source path for the terraform-dbtcloud-yaml module.
                          If None, calculates relative path from output directory.
            provider_version: dbtcloud provider version constraint.
        """
        self.module_source = module_source
        self.provider_version = provider_version
        # Get the repo root (parent of importer directory)
        self._repo_root = Path(__file__).parent.parent.resolve()

    def convert(
        self,
        yaml_file: str,
        output_dir: str,
        target_host_url: Optional[str] = None,
        target_account_id: Optional[int] = None,
        target_token: Optional[str] = None,
        connection_credentials: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Create a Terraform deployment directory.

        Args:
            yaml_file: Path to the normalized YAML configuration file.
            output_dir: Directory to create the Terraform files in.
            target_host_url: Target dbt Cloud host URL (for reference only, uses env vars).
            target_account_id: Target dbt Cloud account ID (for reference only, uses env vars).
            target_token: Target dbt Cloud API token (not stored - uses env vars).
            connection_credentials: Optional dict of connection keys to credential values.
                                   If None, reads from .env file.
        """
        yaml_path = Path(yaml_file).resolve()
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)

        # Copy YAML file to output directory (skip if already there)
        yaml_dest = output_path / "dbt-cloud-config.yml"
        if yaml_path != yaml_dest:
            shutil.copy2(yaml_path, yaml_dest)

        # Load connection keys from YAML to determine which credentials are needed
        connection_keys = self._extract_connection_keys(yaml_path)

        # Load connection credentials from .env if not provided
        if connection_credentials is None:
            connection_credentials = self._load_connection_credentials_from_env(connection_keys)

        # Calculate relative path from output dir to repo root
        # This follows the same pattern as test/e2e_test which uses "../.."
        if self.module_source:
            module_source = self.module_source
        else:
            try:
                # Calculate relative path
                module_source = str(Path("..") / output_path.relative_to(self._repo_root).parent)
                # Simplify: if output is terraform_output, relative is ".."
                # Count how many levels deep we are from repo root
                rel_parts = output_path.relative_to(self._repo_root).parts
                module_source = "/".join([".."] * len(rel_parts))
            except ValueError:
                # Output dir is outside repo, use absolute path
                module_source = str(self._repo_root)

        # Generate main.tf (following test/e2e_test/main.tf pattern)
        self._write_main_tf(output_path, module_source, connection_keys, connection_credentials)
        
        # Generate secrets.auto.tfvars with connection credentials (auto-loaded by Terraform)
        if connection_credentials:
            self._write_secrets_tfvars(output_path, connection_credentials)

    def _extract_connection_keys(self, yaml_path: Path) -> list:
        """Extract connection keys from the YAML file.

        Args:
            yaml_path: Path to the YAML configuration file.

        Returns:
            List of connection key strings.
        """
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            connections = data.get("globals", {}).get("connections", [])
            return [conn.get("key") for conn in connections if conn.get("key")]
        except Exception:
            return []

    def _load_connection_credentials_from_env(
        self,
        connection_keys: list,
    ) -> Dict[str, Dict[str, Any]]:
        """Load connection credentials from .env file.

        Args:
            connection_keys: List of connection keys to look for.

        Returns:
            Dict mapping connection keys to their credential values.
        """
        try:
            from importer.web.env_manager import load_connection_configs
            
            all_configs = load_connection_configs()
            result = {}
            
            for key in connection_keys:
                # Normalize key for lookup (env_manager normalizes to lowercase)
                normalized_key = key.lower().replace("-", "_")
                if normalized_key in all_configs:
                    config = all_configs[normalized_key]
                    # Filter to only include sensitive fields
                    sensitive_config = {
                        field: value
                        for field, value in config.items()
                        if field in SENSITIVE_CONNECTION_FIELDS and value
                    }
                    if sensitive_config:
                        result[key] = sensitive_config
            
            return result
        except ImportError:
            return {}
        except Exception:
            return {}

    def _write_main_tf(
        self,
        output_path: Path,
        module_source: str,
        connection_keys: list,
        connection_credentials: Dict[str, Dict[str, Any]],
    ) -> None:
        """Write the main.tf file following the e2e test pattern.

        Args:
            output_path: Directory to write the file to.
            module_source: Terraform module source path.
            connection_keys: List of connection keys from YAML.
            connection_credentials: Dict of connection credentials.
        """
        # Build connection_credentials block for module call
        credentials_block = self._build_connection_credentials_block(connection_credentials)
        
        # Build variable definitions for connection credentials
        credential_vars = self._build_credential_variable_definitions(connection_keys, connection_credentials)

        content = f'''# Deployment Configuration
# Generated by dbt Magellan
#
# Credentials are provided via environment variables:
#   TF_VAR_dbt_account_id - Target account ID
#   TF_VAR_dbt_token      - API token (service token or PAT)
#   TF_VAR_dbt_host_url   - Host URL (e.g., https://cloud.getdbt.com)
#   TF_VAR_dbt_pat        - Optional: PAT for GitHub App integration
#   TF_VAR_connection_credentials - Optional: Connection OAuth/SSO credentials

terraform {{
  required_version = ">= 1.5"
  required_providers {{
    dbtcloud = {{
      source  = "dbt-labs/dbtcloud"
      version = "{self.provider_version}"
    }}
  }}
}}

provider "dbtcloud" {{
  account_id = var.dbt_account_id
  token      = var.dbt_token
  host_url   = var.dbt_host_url
}}

variable "dbt_account_id" {{
  description = "dbt Cloud account ID"
  type        = number
}}

variable "dbt_token" {{
  description = "dbt Cloud API token"
  type        = string
  sensitive   = true
}}

variable "dbt_host_url" {{
  description = "dbt Cloud API URL (including /api suffix)"
  type        = string
  default     = "https://cloud.getdbt.com/api"
}}

variable "dbt_pat" {{
  description = "dbt Cloud Personal Access Token (dbtu_*) for GitHub App integration"
  type        = string
  sensitive   = true
  default     = null
}}

variable "connection_credentials" {{
  description = "Map of connection keys to their sensitive credential values (OAuth secrets, etc.)"
  type = map(object({{
    oauth_client_id     = optional(string)
    oauth_client_secret = optional(string)
    client_id           = optional(string)
    client_secret       = optional(string)
    private_key_id      = optional(string)
    private_key         = optional(string)
    application_id      = optional(string)
    application_secret  = optional(string)
  }}))
  default   = {{}}
  sensitive = true
}}
{credential_vars}
module "dbt_cloud" {{
  source = "{module_source}"

  # Pass credentials to the module
  dbt_account_id = var.dbt_account_id
  dbt_token      = var.dbt_token
  dbt_host_url   = var.dbt_host_url
  dbt_pat        = var.dbt_pat

  yaml_file   = "${{path.module}}/dbt-cloud-config.yml"
  target_name = "deployment"

  # Credential token mapping (add secrets here if needed)
  token_map = {{
    # Example: "databricks_token" = var.databricks_token
  }}

  # Connection credentials (OAuth/SSO secrets)
{credentials_block}
}}

# Outputs for verification
output "project_ids" {{
  description = "Map of project keys to IDs"
  value       = module.dbt_cloud.v2_project_ids
}}

output "environment_ids" {{
  description = "Map of environment keys to IDs"
  value       = module.dbt_cloud.v2_environment_ids
}}

output "job_ids" {{
  description = "Map of job keys to IDs"
  value       = module.dbt_cloud.v2_job_ids
}}

output "connection_ids" {{
  description = "Map of connection keys to IDs"
  value       = module.dbt_cloud.v2_connection_ids
}}

output "repository_ids" {{
  description = "Map of repository keys to IDs"
  value       = module.dbt_cloud.v2_repository_ids
}}
'''
        (output_path / "main.tf").write_text(content)

    def _build_connection_credentials_block(
        self,
        connection_credentials: Dict[str, Dict[str, Any]],
    ) -> str:
        """Build the connection_credentials block for the module call.

        Args:
            connection_credentials: Dict of connection credentials.

        Returns:
            Terraform HCL string for the connection_credentials block.
        """
        if not connection_credentials:
            return "  connection_credentials = var.connection_credentials"
        
        # Build a merged block that combines var.connection_credentials with any
        # statically known credentials (though we prefer using the variable)
        return "  connection_credentials = var.connection_credentials"

    def _build_credential_variable_definitions(
        self,
        connection_keys: list,
        connection_credentials: Dict[str, Dict[str, Any]],
    ) -> str:
        """Build variable definitions for connection credentials.

        This generates helpful comments showing which connections have credentials
        and how to set them via environment variables.

        Args:
            connection_keys: List of connection keys from YAML.
            connection_credentials: Dict of connection credentials.

        Returns:
            Terraform HCL string with variable definitions and comments.
        """
        if not connection_keys:
            return ""
        
        lines = [
            "",
            "# Connection credential hints (set via TF_VAR_connection_credentials):",
            "# Example JSON format for TF_VAR_connection_credentials:",
            "# {",
        ]
        
        for key in connection_keys:
            creds = connection_credentials.get(key, {})
            if creds:
                cred_fields = ", ".join(f'"{k}": "..."' for k in creds.keys())
                lines.append(f'#   "{key}": {{ {cred_fields} }},')
            else:
                lines.append(f'#   "{key}": {{ }},  # No sensitive credentials detected')
        
        lines.append("# }")
        lines.append("")
        
        return "\n".join(lines)

    def _write_secrets_tfvars(
        self,
        output_path: Path,
        connection_credentials: Dict[str, Dict[str, Any]],
    ) -> None:
        """Write a secrets.auto.tfvars file with connection credentials.

        This file is auto-loaded by Terraform and should be gitignored.
        The .auto.tfvars extension ensures automatic loading.

        Args:
            output_path: Directory to write the file to.
            connection_credentials: Dict of connection credentials.
        """
        if not connection_credentials:
            return

        # Build HCL map for connection_credentials
        lines = [
            "# Auto-generated connection credentials",
            "# WARNING: This file contains sensitive values - add to .gitignore!",
            "",
            "connection_credentials = {",
        ]

        for conn_key, creds in connection_credentials.items():
            lines.append(f'  "{conn_key}" = {{')
            for field, value in creds.items():
                # Escape quotes in values
                escaped_value = str(value).replace('\\', '\\\\').replace('"', '\\"')
                lines.append(f'    {field} = "{escaped_value}"')
            lines.append("  }")

        lines.append("}")
        lines.append("")

        secrets_file = output_path / "secrets.auto.tfvars"
        secrets_file.write_text("\n".join(lines))
        
        # Also ensure .gitignore exists with secrets.auto.tfvars
        gitignore_path = output_path / ".gitignore"
        gitignore_content = "# Sensitive credential files\nsecrets.auto.tfvars\n*.tfvars\n!example.tfvars\n"
        if not gitignore_path.exists():
            gitignore_path.write_text(gitignore_content)
        else:
            existing = gitignore_path.read_text()
            if "secrets.auto.tfvars" not in existing:
                gitignore_path.write_text(existing + "\n" + gitignore_content)
