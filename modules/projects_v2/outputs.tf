#############################################
# Module Outputs
# 
# Exposes resource IDs for reference by other modules or outputs.
#############################################

# Global resource IDs
output "connection_ids" {
  description = "Map of connection keys to connection IDs"
  value = {
    for key, conn in dbtcloud_global_connection.connections :
    key => conn.id
  }
}

output "repository_ids" {
  description = "Map of project keys to repository IDs"
  value = {
    for key, repo in dbtcloud_repository.repositories :
    key => repo.id
  }
}

output "service_token_ids" {
  description = "Map of service token keys to service token IDs"
  value = {
    for key, token in dbtcloud_service_token.service_tokens :
    key => token.id
  }
}

output "group_ids" {
  description = "Map of group keys to group IDs"
  value = {
    for key, group in dbtcloud_group.groups :
    key => group.id
  }
}

output "notification_ids" {
  description = "Map of notification keys to notification IDs"
  value = {
    for key, notif in dbtcloud_notification.notifications :
    key => notif.id
  }
}

# Project resource IDs
output "project_ids" {
  description = "Map of project keys to project IDs"
  value = {
    for key, project in dbtcloud_project.projects :
    key => project.id
  }
}

output "environment_ids" {
  description = "Map of project_key_environment_key to environment IDs"
  value = {
    for key, env in dbtcloud_environment.environments :
    key => env.id
  }
}

output "job_ids" {
  description = "Map of project_key_environment_key_job_key to job IDs"
  value = {
    for key, job in dbtcloud_job.jobs :
    key => job.id
  }
}

output "credential_ids" {
  description = "Map of project_key_environment_key to credential IDs"
  value = {
    for key, cred in dbtcloud_databricks_credential.credentials :
    key => cred.credential_id
  }
}

