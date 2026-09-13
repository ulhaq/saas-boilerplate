import type { PermissionOut } from './permission'

export interface RoleBase {
  name: string
  description?: string | null
}

export type RoleIn = RoleBase

export interface RolePatch {
  name?: string
  description?: string | null
}

export interface RolePermissionIn {
  permission_ids: number[]
}

export interface RoleOut extends RoleBase {
  id: number
  organization_id: number
  is_protected: boolean
  permissions: PermissionOut[]
  created_at: string
  updated_at: string
}
