import { defineStore } from 'pinia'
import { rolesApi } from '@/platform/api/roles'
import type {
  PaginatedResponse,
  RoleOut,
  RoleIn,
  RolePatch,
  RolePermissionIn,
} from '@/platform/types'

type ListParams = Record<string, string | number | undefined>

// Gateway store for the roles domain (see frontend/CLAUDE.md "Data Access").
// Components never import `@/platform/api/roles` directly. Passthrough actions return
// unwrapped domain data.
export const useRolesStore = defineStore('roles', () => {
  async function list(params: ListParams = {}): Promise<PaginatedResponse<RoleOut>> {
    const { data: roles } = await rolesApi.list(params)
    return roles
  }

  async function create(data: RoleIn): Promise<RoleOut> {
    const { data: role } = await rolesApi.create(data)
    return role
  }

  async function patch(id: number, data: RolePatch): Promise<RoleOut> {
    const { data: role } = await rolesApi.patch(id, data)
    return role
  }

  async function remove(id: number): Promise<void> {
    await rolesApi.delete(id)
  }

  async function setPermissions(id: number, data: RolePermissionIn): Promise<RoleOut> {
    const { data: role } = await rolesApi.setPermissions(id, data)
    return role
  }

  return { list, create, patch, remove, setPermissions }
})
