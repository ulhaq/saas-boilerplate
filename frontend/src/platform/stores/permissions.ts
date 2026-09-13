import { defineStore } from 'pinia'
import { permissionsApi } from '@/platform/api/permissions'
import type { PaginatedResponse, PermissionOut } from '@/platform/types'

type ListParams = Record<string, string | number | undefined>

// Gateway store for the permissions domain (see frontend/CLAUDE.md "Data
// Access"). Read-only; components never import `@/platform/api/permissions` directly.
export const usePermissionsStore = defineStore('permissions', () => {
  async function list(params: ListParams = {}): Promise<PaginatedResponse<PermissionOut>> {
    const { data: permissions } = await permissionsApi.list(params)
    return permissions
  }

  return { list }
})
