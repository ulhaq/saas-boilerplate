import { apiClient } from './client'
import type { ApiTokenCreate, ApiTokenCreatedResponse, ApiTokenResponse } from '@/platform/types'

export const apiTokensApi = {
  list() {
    return apiClient.get<ApiTokenResponse[]>('/api-tokens')
  },

  create(data: ApiTokenCreate) {
    return apiClient.post<ApiTokenCreatedResponse>('/api-tokens', data)
  },

  revoke(id: number) {
    return apiClient.delete(`/api-tokens/${id}`)
  },
}
