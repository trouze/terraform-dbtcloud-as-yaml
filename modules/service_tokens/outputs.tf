output "service_token_ids" {
  description = "Map of service token key to dbt Cloud service token ID"
  value = merge(
    { for k, t in dbtcloud_service_token.service_tokens : k => t.id },
    { for k, t in dbtcloud_service_token.protected_service_tokens : k => t.id }
  )
}

output "service_tokens_provenance" {
  description = "Per-token provenance (YAML key, logical identity, optional external id) merged with dbt_service_token_id — mirrors v2 resource_metadata without provider support"
  value = {
    for key, meta in local.service_tokens_provenance :
    key => merge(
      meta,
      {
        dbt_service_token_id = coalesce(
          try(dbtcloud_service_token.service_tokens[key].id, null),
          try(dbtcloud_service_token.protected_service_tokens[key].id, null),
        )
      },
    )
  }
}
