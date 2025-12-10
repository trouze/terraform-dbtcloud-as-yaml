#############################################
# Jobs
# 
# Creates jobs for each project/environment combination.
# Handles cross-references (environments, notifications, deferral).
#############################################

locals {
  # Flatten all jobs across all projects and environments
  all_jobs = flatten([
    for project in var.projects : [
      for env in project.environments : [
        for job in try(env.jobs, []) : {
          project_key     = project.key
          project_id      = dbtcloud_project.projects[project.key].id
          environment_key = env.key
          environment_id  = dbtcloud_environment.environments["${project.key}_${env.key}"].id
          job_key         = job.key
          job_data        = job
        }
      ] if try(env.jobs, null) != null
    ]
  ])

  # Create map keyed by project_key_environment_key_job_key
  jobs_map = {
    for item in local.all_jobs :
    "${item.project_key}_${item.environment_key}_${item.job_key}" => item
  }

  # Helper to resolve deferring environment ID by key
  resolve_deferring_environment_id = {
    for key, item in local.jobs_map :
    key => (
      try(item.job_data.deferring_environment_key, null) != null ?
      lookup(
        {
          for env_item in local.all_environments :
          "${env_item.project_key}_${env_item.env_key}" => dbtcloud_environment.environments["${env_item.project_key}_${env_item.env_key}"].id
        },
        "${item.project_key}_${item.job_data.deferring_environment_key}",
        null
      ) : null
    )
  }

  # Helper to resolve deferring job ID by key
  resolve_deferring_job_id = {
    for key, item in local.jobs_map :
    key => (
      try(item.job_data.deferring_job_key, null) != null ?
      lookup(
        local.jobs_map,
        "${item.project_key}_${item.job_data.deferring_environment_key}_${item.job_data.deferring_job_key}",
        null
      ) != null ?
      dbtcloud_job.jobs["${item.project_key}_${item.job_data.deferring_environment_key}_${item.job_data.deferring_job_key}"].id :
      null : null
    )
  }

  # Helper to resolve notification IDs by keys
  resolve_notification_ids = {
    for key, item in local.jobs_map :
    key => [
      for notif_key in try(item.job_data.notification_keys, []) :
      # Check global notifications first
      try(dbtcloud_notification.notifications[notif_key].id, null) != null ?
      dbtcloud_notification.notifications[notif_key].id :
      # Then check project-scoped notifications (if implemented)
      null
    ]
  }
}

# Create jobs
resource "dbtcloud_job" "jobs" {
  for_each = local.jobs_map

  project_id     = each.value.project_id
  name           = each.value.job_data.name
  environment_id = each.value.environment_id
  execute_steps  = each.value.job_data.execute_steps
  triggers       = each.value.job_data.triggers

  # Optional fields
  description                = try(each.value.job_data.description, null)
  dbt_version                = try(each.value.job_data.dbt_version, null)
  deferring_environment_id   = local.resolve_deferring_environment_id[each.key]
  deferring_job_id           = local.resolve_deferring_job_id[each.key]
  errors_on_lint_failure     = try(each.value.job_data.errors_on_lint_failure, true)
  generate_docs              = try(each.value.job_data.generate_docs, false)
  is_active                  = try(each.value.job_data.is_active, true)
  num_threads                = try(each.value.job_data.num_threads, 4)
  run_compare_changes        = try(each.value.job_data.run_compare_changes, false)
  run_generate_sources       = try(each.value.job_data.run_generate_sources, false)
  run_lint                   = try(each.value.job_data.run_lint, false)
  schedule_cron              = try(each.value.job_data.schedule_cron, null)
  schedule_days              = try(each.value.job_data.schedule_days, null)
  schedule_hours             = try(each.value.job_data.schedule_hours, null)
  schedule_interval          = try(each.value.job_data.schedule_interval, null)
  schedule_type              = try(each.value.job_data.schedule_type, null)
  target_name                = try(each.value.job_data.target_name, null)
  timeout_seconds            = try(each.value.job_data.timeout_seconds, 0)
  triggers_on_draft_pr       = try(each.value.job_data.triggers_on_draft_pr, false)
  self_deferring              = try(each.value.job_data.self_deferring, null)
}

# Note: Notification job associations are handled in globals.tf
# The dbtcloud_notification resource in globals.tf includes job IDs
# from the on_success, on_failure, etc. fields in the YAML.
# If jobs reference notifications via notification_keys, those associations
# should be included in the notification definition in the YAML.

