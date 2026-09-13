export interface ApiTokenCreate {
  name: string
  permissions: string[]
  expires_at?: string | null
}

export interface ApiTokenResponse {
  id: number
  name: string
  token_prefix: string
  permissions: string[]
  created_at: string
  expires_at: string | null
  last_used_at: string | null
  revoked_at: string | null
  is_expired: boolean
}

export interface ApiTokenCreatedResponse extends ApiTokenResponse {
  token: string
}
