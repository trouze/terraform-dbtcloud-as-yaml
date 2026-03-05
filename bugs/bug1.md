Not all repo objects are coming in and being associated properly.  THis is an example from the source perspective.

There are 86 projects, but only 62 repo objects in 
Data: /Users/operator/Documents/git/dbt-labs/terraform-dbtcloud-yaml/projects/ps-sandbox/outputs/source/account_51798_run_002__json__20260305_021257.json
Summary: /Users/operator/Documents/git/dbt-labs/terraform-dbtcloud-yaml/projects/ps-sandbox/outputs/source/account_51798_run_002__summary__20260305_021257.md

{
  "element_mapping_id": "62019a83025b",
  "env_var_count": 0,
  "environment_count": 1,
  "extended_attributes": [],
  "id": 254274,
  "job_count": 0,
  "key": "benoit_s_databricks_sandbox_dx",
  "metadata": {
    "account_id": 51798,
    "connection": {
      "account_id": 51798,
      "adapter_version": "databricks_v0",
      "catalog_ingestion_enabled": false,
      "cost_insights_enabled": false,
      "cost_management_enabled": false,
      "created_at": "2023-05-31 16:23:34.938817+00:00",
      "created_by_id": 54461,
      "created_by_service_token_id": null,
      "details": {
        "adapter_id": 7980,
        "connection_details": {
          "field_groups": null,
          "field_order": [
            "type",
            "host",
            "http_path",
            "catalog",
            "client_id",
            "client_secret"
          ],
          "fields": {
            "catalog": {
              "metadata": {
                "depends_on": null,
                "description": "Catalog name if Unity Catalog is enabled in your Databricks workspace.  Only available in dbt version 1.1 and later.",
                "encrypt": false,
                "field_type": "text",
                "is_searchable": null,
                "label": "Catalog",
                "overrideable": true,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": null,
                  "required": false
                }
              },
              "value": ""
            },
            "client_id": {
              "metadata": {
                "depends_on": null,
                "description": "Required to enable Databricks OAuth authentication for IDE developers.",
                "encrypt": true,
                "field_type": "text",
                "is_searchable": null,
                "label": "OAuth Client ID",
                "overrideable": false,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": null,
                  "required": false
                }
              },
              "value": ""
            },
            "client_secret": {
              "metadata": {
                "depends_on": null,
                "description": "Required to enable Databricks OAuth authentication for IDE developers.",
                "encrypt": true,
                "field_type": "text",
                "is_searchable": null,
                "label": "OAuth Client Secret",
                "overrideable": false,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": null,
                  "required": false
                }
              },
              "value": ""
            },
            "host": {
              "metadata": {
                "depends_on": null,
                "description": "The hostname of the Databricks cluster or SQL warehouse.",
                "encrypt": false,
                "field_type": "text",
                "is_searchable": null,
                "label": "Server Hostname",
                "overrideable": false,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": "databricks_hostname",
                  "required": true
                }
              },
              "value": "dbc-88636ef1-59c4.cloud.databricks.com"
            },
            "http_path": {
              "metadata": {
                "depends_on": null,
                "description": "The HTTP path of the Databricks cluster or SQL warehouse.",
                "encrypt": false,
                "field_type": "text",
                "is_searchable": null,
                "label": "HTTP Path",
                "overrideable": false,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": "databricks_http_path",
                  "required": true
                }
              },
              "value": "/sql/1.0/warehouses/b633a121c93855a0"
            },
            "type": {
              "metadata": {
                "depends_on": null,
                "description": "",
                "encrypt": false,
                "field_type": "hidden",
                "is_searchable": null,
                "label": "Connection type",
                "overrideable": false,
                "validation": {
                  "max_length": null,
                  "min_length": null,
                  "pattern": null,
                  "required": false
                }
              },
              "value": "databricks"
            }
          }
        },
        "created_at": "2023-05-31 16:23:34.938817+00:00",
        "id": null,
        "is_configured_for_oauth": false,
        "updated_at": "2023-05-31 16:23:34.938836+00:00"
      },
      "id": 139965,
      "name": "Databricks",
      "oauth_configuration_id": null,
      "oauth_redirect_uri": "https://cloud.getdbt.com/complete/databricks",
      "platform_metadata_credentials_id": null,
      "private_link_endpoint_id": null,
      "project_id": 254274,
      "state": 1,
      "type": "adapter",
      "updated_at": "2023-05-31 16:23:34.938836+00:00"
    },
    "connection_id": 139965,
    "created_at": "2023-05-31 16:20:59.956258+00:00",
    "dbt_project_subdirectory": null,
    "description": "",
    "docs_job": null,
    "docs_job_id": null,
    "environments": null,
    "freshness_job": null,
    "freshness_job_id": null,
    "group_permissions": [],
    "id": 254274,
    "name": "Benoit's databricks sandbox - DX",
    "repository": {
      "account_id": 51798,
      "created_at": "2023-05-31 16:21:29.570648+00:00",
      "deploy_key": {
        "account_id": 51798,
        "id": 153302,
        "public_key": "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDhWkEuJv3GORTDx+HBmkXXH6gcTiU9N7GoE5LC7f//HSZQzJNuihJy/YNeip4N30wDbkHvxM/Z8XMhkbwSqO8re3dGY8pz2Y/PbSPglDIBfPXPqTsCEyBP6lr8V2/LiPeCaoteZPBy5cnOzKcooFl70CiT2y2HFGxIeQG8MlMlDUy7gZwR3jUXynr3dy1vT/HRPkMyxmXGCaAcaEQJtNSp1ZtVGZriXk6QzIBzChLoyZIDg5mOhuiq7qGzYl8XM2PcGRrWxoCw8cqNszwpgmREQ+yjiRjurvyj5lGNYqx6Pi2Fm6HLnhAGb5MxlXGWo25ZGpI3FPl9uHlQssc4pTc4yrRvXDKiNfvYbCYJZ82saXitJy6Hl0/idAtGwWvJ+GGBMTWOCn5Vicxz07IMtu/7Dl2KEsf8izup6ginduGDM6jtca25VG4OYE7nKA4Umlt/252JsSQkNCWvL56bhK7SXaB6O79foyTsm7xdkO+IDBAhMrK68DHbJmTcwDIXtxG/tALKS50Y2g1Co3o2V8pRn0j+11ZvRnYp5C0gt1M2HPt7RjoLgpmeY7YQH4dp1lxXmesl407540mmk6vB6uQ0WYZyg00+h1KPVbOuuxDRN5x+VWL1SYe46CePVqBmBpq9Neq2q7uSe5/HqF+CqQ+qX8P88+7WAE18mkH4RX2Udw==",
        "state": 1
      },
      "deploy_key_id": 153302,
      "full_name": "dbt-labs/jaffle_shop",
      "git_clone_strategy": "github_app",
      "git_provider": null,
      "git_provider_id": null,
      "github_installation_id": 267820,
      "github_repo": "dbt-labs/jaffle_shop",
      "github_webhook_id": null,
      "gitlab": null,
      "id": 152400,
      "is_private_link_enabled": false,
      "name": "jaffle_shop",
      "private_link_endpoint_id": null,
      "project_id": 254274,
      "pull_request_url_template": "https://github.com/dbt-labs/jaffle_shop/compare/{{destination}}...{{source}}",
      "remote_backend": "github",
      "remote_url": "git://github.com/dbt-labs/jaffle_shop.git",
      "repository_credentials_id": null,
      "state": 1,
      "updated_at": "2023-05-31 16:21:29.570668+00:00",
      "web_url": "https://github.com/dbt-labs/jaffle_shop"
    },
    "repository_id": 152400,
    "semantic_layer_config_id": null,
    "skipped_setup": true,
    "state": 1,
    "type": 0,
    "updated_at": "2023-05-31 16:23:35.426831+00:00"
  },
  "name": "Benoit's databricks sandbox - DX",
  "repository_key": null
}