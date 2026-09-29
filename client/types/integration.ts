export interface IntegrationWithStatus {
  integration_type: string
  display_name: string
  description: string
  icon_url: string | null
  is_connected: boolean
  status: "connected" | "not_connected" | "error" | "setup"
  connected_at: string | null
}