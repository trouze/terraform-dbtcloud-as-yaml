output "user_group_ids" {
  description = "Map of assignment key (YAML key or string user_id) to dbtcloud_user_groups resource ID"
  value       = { for k, ug in dbtcloud_user_groups.user_groups : k => ug.id }
}

output "user_groups_provenance" {
  description = "Per-assignment provenance (YAML key, logical identity, optional external id) merged with dbt_user_groups_id — mirrors v2 resource_metadata without provider support"
  value = {
    for key, meta in local.user_groups_provenance :
    key => merge(
      meta,
      { dbt_user_groups_id = dbtcloud_user_groups.user_groups[key].id },
    )
  }
}
