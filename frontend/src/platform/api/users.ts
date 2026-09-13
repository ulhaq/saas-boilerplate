import { apiClient } from './client'
import type {
  PaginatedResponse,
  UserOut,
  UserPatch,
  UserRoleIn,
  OrganizationOut,
  ChangePasswordIn,
} from '@/platform/types'

interface ListParams {
  page_number?: number
  page_size?: number
  sort?: string
  q?: string
  [key: string]: string | number | undefined
}

export const usersApi = {
  list(params: ListParams = {}) {
    return apiClient.get<PaginatedResponse<UserOut>>('/users', { params })
  },

  getMe() {
    return apiClient.get<UserOut>('/users/me')
  },

  getMyOrganizations() {
    return apiClient.get<OrganizationOut[]>('/organizations')
  },

  get(id: number) {
    return apiClient.get<UserOut>(`/users/${id}`)
  },

  patch(id: number, data: UserPatch) {
    return apiClient.patch<UserOut>(`/users/${id}`, data)
  },

  patchMe(data: UserPatch) {
    return apiClient.patch<UserOut>('/users/me', data)
  },

  changePassword(data: ChangePasswordIn) {
    return apiClient.put<UserOut>('/users/me/change-password', data)
  },

  removeFromOrganization(id: number) {
    return apiClient.delete(`/users/${id}`)
  },

  setRoles(id: number, data: UserRoleIn) {
    return apiClient.post<UserOut>(`/users/${id}/roles`, data)
  },

  invite(data: { email: string; role_ids: number[] }) {
    return apiClient.post('/users/invite', data)
  },
}
