variable "dbt_account_id" {
  description = "dbt Cloud account ID"
  type        = number
  sensitive   = true
}

variable "dbt_token" {
  description = "dbt Cloud API token"
  type        = string
  sensitive   = true
}

variable "dbt_pat" {
  description = "dbt Cloud Personal Access Token (optional, defaults to dbt_api_token)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "dbt_host_url" {
  description = "dbt Cloud host URL (e.g., https://cloud.getdbt.com)"
  type        = string
  default     = "https://cloud.getdbt.com"
}

variable "yaml_file_path" {
  description = "Path to the dbt configuration YAML file"
  type        = string
  default     = "./dbt-config.yml"
}

variable "token_map" {
  description = "Map of database credentials (warehouse tokens, API keys, etc.)"
  type        = map(string)
  sensitive   = true
  default     = {}
}

variable "target_name" {
  description = "Override the default target name from dbt_project.yml"
  type        = string
  default     = ""
}
