import { apiClient } from './client'
import type {
  PaginatedResponse,
  OrganizationOut,
  OrganizationBase,
  OrganizationPatch,
  UserOut,
} from '@/platform/types'

export const organizationsApi = {
  list() {
    return apiClient.get<OrganizationOut[]>('/organizations')
  },

  get(id: number) {
    return apiClient.get<OrganizationOut>(`/organizations/${id}`)
  },

  create(data: OrganizationBase) {
    return apiClient.post<OrganizationOut>('/organizations', data)
  },

  patch(id: number, data: OrganizationPatch) {
    return apiClient.patch<OrganizationOut>(`/organizations/${id}`, data)
  },

  delete(id: number) {
    return apiClient.delete(`/organizations/${id}`)
  },

  getUsers(organizationId: number) {
    return apiClient.get<PaginatedResponse<UserOut>>(`/organizations/${organizationId}/users`)
  },

  transferOwnership(organizationId: number, userId: number) {
    return apiClient.post(`/organizations/${organizationId}/transfer-ownership`, {
      user_id: userId,
    })
  },
}
