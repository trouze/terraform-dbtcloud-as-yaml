output "oauth_configuration_ids" {
  description = "Map of OAuth configuration key to dbt Cloud OAuth configuration ID"
  value = merge(
    { for k, o in dbtcloud_oauth_configuration.oauth_configurations : k => o.id },
    { for k, o in dbtcloud_oauth_configuration.protected_oauth_configurations : k => o.id },
  )
}

output "oauth_configurations_provenance" {
  description = "Per-config provenance (YAML key, logical identity, optional external id) merged with dbt_oauth_configuration_id — mirrors v2 resource_metadata without provider support"
  value = {
    for key, meta in local.oauth_configurations_provenance :
    key => merge(
      meta,
      {
        dbt_oauth_configuration_id = coalesce(
          try(dbtcloud_oauth_configuration.oauth_configurations[key].id, null),
          try(dbtcloud_oauth_configuration.protected_oauth_configurations[key].id, null),
        )
      },
    )
  }
}
