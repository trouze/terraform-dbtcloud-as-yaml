output "connection_ids" {
  description = "Map of connection key to dbt Cloud global connection ID"
  value = merge(
    { for k, c in dbtcloud_global_connection.connections : k => tostring(c.id) },
    { for k, c in dbtcloud_global_connection.protected_connections : k => tostring(c.id) }
  )
}

output "connections_provenance" {
  description = "Per-connection provenance (YAML key, logical identity, optional external id) merged with dbt_connection_id — mirrors v2 resource_metadata without provider support"
  value = {
    for key, meta in local.connections_provenance :
    key => merge(
      meta,
      {
        dbt_connection_id = coalesce(
          try(dbtcloud_global_connection.connections[key].id, null),
          try(dbtcloud_global_connection.protected_connections[key].id, null),
        )
      },
    )
  }
}
