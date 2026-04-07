output "ip_rule_ids" {
  description = "Map of IP rule key to dbt Cloud IP restriction rule ID"
  value = merge(
    { for k, r in dbtcloud_ip_restrictions_rule.ip_rules : k => r.id },
    { for k, r in dbtcloud_ip_restrictions_rule.protected_ip_rules : k => r.id },
  )
}

output "ip_rules_provenance" {
  description = "Per-rule provenance (YAML key, logical identity, optional external id) merged with dbt_rule_id — mirrors v2 resource_metadata without provider support"
  value = {
    for key, meta in local.ip_rules_provenance :
    key => merge(
      meta,
      {
        dbt_rule_id = coalesce(
          try(dbtcloud_ip_restrictions_rule.ip_rules[key].id, null),
          try(dbtcloud_ip_restrictions_rule.protected_ip_rules[key].id, null),
        )
      },
    )
  }
}
