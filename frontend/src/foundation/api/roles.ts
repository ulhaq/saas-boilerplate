import { api } from './client'
import type { RoleIn, RolePatch, RolePermissionIn } from '@/foundation/types'

type ListParams = Record<string, string | number | undefined>

export const rolesApi = {
  list(params: ListParams = {}) {
    return api.get('/roles', { query: params })
  },

  get(id: number) {
    return api.get('/roles/{identifier}', { path: { identifier: id } })
  },

  create(data: RoleIn) {
    return api.post('/roles', { body: data })
  },

  patch(id: number, data: RolePatch) {
    return api.patch('/roles/{identifier}', { path: { identifier: id }, body: data })
  },

  delete(id: number) {
    return api.delete('/roles/{identifier}', { path: { identifier: id } })
  },

  setPermissions(id: number, data: RolePermissionIn) {
    return api.post('/roles/{identifier}/permissions', { path: { identifier: id }, body: data })
  },
}
