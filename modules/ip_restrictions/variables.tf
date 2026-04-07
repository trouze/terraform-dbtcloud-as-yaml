variable "ip_rules_data" {
  description = "List of IP restriction rule configurations from YAML ip_restrictions[]. Optional protected: true applies lifecycle.prevent_destroy; optional id is emitted in ip_rules_provenance.source_id."
  type        = any
  default     = []
}
