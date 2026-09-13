export interface NotificationOut {
  id: number
  user_id: number
  organization_id: number
  type: string
  payload: unknown
  read_at: string | null
  created_at: string
}

export interface UnreadCountOut {
  count: number
}
