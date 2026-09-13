import { apiClient } from './client'
import type { PaginatedResponse, PermissionOut } from '@/platform/types'

interface ListParams {
  page_number?: number
  page_size?: number
  sort?: string
  q?: string
  [key: string]: string | number | undefined
}

export const permissionsApi = {
  list(params: ListParams = {}) {
    return apiClient.get<PaginatedResponse<PermissionOut>>('/permissions', { params })
  },

  get(id: number) {
    return apiClient.get<PermissionOut>(`/permissions/${id}`)
  },
}
