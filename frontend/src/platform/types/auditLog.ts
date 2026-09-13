export interface AuditLogUserOut {
  id: number
  name: string
  email: string
}

export interface AuditLogOut {
  id: number
  organization_id: number | null
  user_id: number | null
  user: AuditLogUserOut | null
  action: string
  resource_type: string | null
  resource_id: number | null
  ip_address: string | null
  details: Record<string, unknown> | null
  created_at: string
}
