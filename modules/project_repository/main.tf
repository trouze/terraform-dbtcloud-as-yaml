terraform {
  required_version = ">= 1.7"
  required_providers {
    dbtcloud = {
      source  = "dbt-labs/dbtcloud"
      version = "~> 1.9"
    }
  }
}

resource "dbtcloud_project_repository" "project_repositories" {
  for_each = var.repository_ids

  project_id    = var.project_ids[each.key]
  repository_id = each.value
}
