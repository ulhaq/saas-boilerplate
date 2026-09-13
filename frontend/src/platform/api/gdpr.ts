import { apiClient } from './client'

export interface UserDataExport {
  user: Record<string, unknown>
  organizations: Record<string, unknown>[]
  api_tokens: Record<string, unknown>[]
  audit_logs: Record<string, unknown>[]
}

export interface DeleteMeIn {
  current_password: string
}

export const gdprApi = {
  exportMyData() {
    return apiClient.get<UserDataExport>('/users/me/export')
  },

  deleteMyAccount(data: DeleteMeIn) {
    return apiClient.delete('/users/me', { data })
  },
}
