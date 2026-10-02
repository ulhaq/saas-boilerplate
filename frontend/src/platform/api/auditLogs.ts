import { api } from './client'

interface ListParams {
  page_number?: number
  page_size?: number
  action?: string
}

export const auditLogsApi = {
  list(params: ListParams = {}) {
    return api.get('/audit-logs', { query: { ...params } })
  },
}
