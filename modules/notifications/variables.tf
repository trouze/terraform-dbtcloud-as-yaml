variable "notifications_data" {
  description = "List of notificationTarget objects from YAML globals.notifications[]. Each entry must have key, type (slack|email|pagerduty|webhook), and target object."
  type        = any
  default     = []
}
