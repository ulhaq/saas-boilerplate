import { apiClient } from './client'
import type { PaginatedResponse } from '@/platform/types'
import type { AuditLogOut } from '@/platform/types/auditLog'

interface ListParams {
  page_number?: number
  page_size?: number
  action?: string
}

export const auditLogsApi = {
  list(params: ListParams = {}) {
    return apiClient.get<PaginatedResponse<AuditLogOut>>('/audit-logs', { params })
  },
}
