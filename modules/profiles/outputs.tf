output "profile_ids" {
  description = "Map of composite key (project_key_profile_key) to dbt Cloud profile_id (numeric API id; use for environment primary_profile_id)"
  value       = { for k, p in dbtcloud_profile.profiles : k => p.profile_id }
}
