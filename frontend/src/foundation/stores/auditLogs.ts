import { defineStore } from 'pinia'
import { auditLogsApi } from '@/foundation/api/auditLogs'
import type { PaginatedResponse } from '@/foundation/types'
import type { AuditLogOut } from '@/foundation/types/auditLog'

type ListParams = Record<string, string | number | undefined>

// Gateway store for the audit-logs domain (see frontend/CLAUDE.md "Data
// Access"). Read-only; components never import `@/foundation/api/auditLogs` directly.
export const useAuditLogsStore = defineStore('auditLogs', () => {
  async function list(params: ListParams = {}): Promise<PaginatedResponse<AuditLogOut>> {
    const { data: logs } = await auditLogsApi.list(params)
    return logs
  }

  return { list }
})
