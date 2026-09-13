export interface OrganizationBase {
  name: string
}

export interface OrganizationPatch {
  name?: string
}

export interface OrganizationOut extends OrganizationBase {
  id: number
  is_owner?: boolean
  created_at: string
  updated_at: string
}
