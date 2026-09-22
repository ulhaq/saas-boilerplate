export interface InvitationRoleOut {
  id: number
  name: string
}

export interface InvitationInviterOut {
  id: number
  name: string
  email: string
}

export interface InvitationOut {
  id: number
  email: string
  role_ids: number[]
  /** role_ids resolved to the org's current roles (deleted roles omitted). */
  roles: InvitationRoleOut[]
  /** null when the inviting user has since been deleted. */
  invited_by: InvitationInviterOut | null
  created_at: string
  expires_at: string
  is_expired: boolean
}
