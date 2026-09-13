import { apiClient } from './client'
import type {
  PaginatedResponse,
  RoleOut,
  RoleIn,
  RolePatch,
  RolePermissionIn,
} from '@/platform/types'

interface ListParams {
  page_number?: number
  page_size?: number
  sort?: string
  q?: string
  [key: string]: string | number | undefined
}

export const rolesApi = {
  list(params: ListParams = {}) {
    return apiClient.get<PaginatedResponse<RoleOut>>('/roles', { params })
  },

  get(id: number) {
    return apiClient.get<RoleOut>(`/roles/${id}`)
  },

  create(data: RoleIn) {
    return apiClient.post<RoleOut>('/roles', data)
  },

  patch(id: number, data: RolePatch) {
    return apiClient.patch<RoleOut>(`/roles/${id}`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/roles/${id}`)
  },

  setPermissions(id: number, data: RolePermissionIn) {
    return apiClient.post<RoleOut>(`/roles/${id}/permissions`, data)
  },
}
