<route lang="yaml">
meta:
  permission: read:audit_log
  breadcrumb: nav.auditLog
</route>

<template>
  <div class="animate-fade-in">
    <PageHeader :title="$t('auditLog.title')" :description="$t('auditLog.description')" />

    <DataTable
      :columns="columns"
      :items="items"
      :total="total"
      :page="pagination.page"
      :page-size="pagination.pageSize"
      :total-pages="totalPages"
      :loading="isLoading"
      :empty-title="$t('auditLog.noLogsFound')"
      :empty-description="$t('auditLog.noLogsDescription')"
      @update:page="goToPage"
      @update:page-size="setPageSize"
    >
      <template #toolbar>
        <Select v-model="selectedAction">
          <SelectTrigger class="w-48 h-9">
            <SelectValue :placeholder="$t('auditLog.filterByAction')" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__all__">{{ $t('auditLog.allActions') }}</SelectItem>
            <SelectItem v-for="action in auditActions" :key="action" :value="action">
              {{ action }}
            </SelectItem>
          </SelectContent>
        </Select>
      </template>
      <template #row="{ item }">
        <TableCell>
          <Badge variant="secondary" class="text-xs font-mono">{{ item.action }}</Badge>
        </TableCell>
        <TableCell>
          <div v-if="item.user">
            <p class="text-sm font-medium">{{ item.user.name }}</p>
            <p class="text-xs text-muted-foreground">{{ item.user.email }}</p>
          </div>
          <span v-else class="text-sm text-muted-foreground">{{ $t('auditLog.noUser') }}</span>
        </TableCell>
        <TableCell class="text-sm text-muted-foreground font-mono">
          <span v-if="item.resource_type">
            {{ item.resource_type }}<span v-if="item.resource_id"> #{{ item.resource_id }}</span>
          </span>
          <span v-else>{{ $t('auditLog.noResource') }}</span>
        </TableCell>
        <TableCell class="text-sm text-muted-foreground font-mono">
          {{ item.ip_address ?? $t('auditLog.noIpAddress') }}
        </TableCell>
        <TableCell>
          <Popover v-if="item.details && Object.keys(item.details).length">
            <PopoverTrigger as-child>
              <Button
                variant="ghost"
                size="sm"
                class="h-7 gap-1.5 px-2 text-xs text-muted-foreground"
              >
                <Info class="w-3.5 h-3.5" />
                {{ $t('auditLog.viewDetails') }}
              </Button>
            </PopoverTrigger>
            <PopoverContent class="w-72 p-0" align="start">
              <div class="px-3 py-2 border-b border-border">
                <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {{ $t('auditLog.columns.details') }}
                </p>
              </div>
              <dl class="divide-y divide-border">
                <div
                  v-for="(val, key) in item.details"
                  :key="key"
                  class="px-3 py-2 grid grid-cols-2 gap-2"
                >
                  <dt class="text-xs font-medium text-muted-foreground truncate">{{ key }}</dt>
                  <dd class="text-xs text-foreground break-all">{{ formatDetailValue(val) }}</dd>
                </div>
              </dl>
            </PopoverContent>
          </Popover>
          <span v-else class="text-sm text-muted-foreground">{{ $t('auditLog.noDetails') }}</span>
        </TableCell>
        <TableCell class="text-muted-foreground text-xs">
          {{ formatDateTime(item.created_at) }}
        </TableCell>
      </template>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Info } from 'lucide-vue-next'
import { Badge } from '@/platform/components/ui/badge'
import { Button } from '@/platform/components/ui/button'
import { TableCell } from '@/platform/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/platform/components/ui/select'
import { Popover, PopoverContent, PopoverTrigger } from '@/platform/components/ui/popover'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import DataTable from '@/platform/components/common/DataTable.vue'
import { useAuditLogsStore } from '@/platform/stores/auditLogs'
import { useDataTable } from '@/platform/composables/useDataTable'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import type { AuditLogOut } from '@/platform/types/auditLog'

const { t } = useI18n()
const auditLogsStore = useAuditLogsStore()
const { formatDateTime } = useFormatDate()

const auditActions = [
  'auth.login',
  'auth.register',
  'auth.password_reset',
  'user.invite',
  'user.update',
  'user.delete',
  'user.role_assign',
  'user.consent',
  'user.export',
  'user.self_delete',
  'role.create',
  'role.update',
  'role.delete',
  'role.permission_assign',
  'api_token.create',
  'api_token.delete',
  'org.update',
]

const columns = [
  { key: 'action', label: t('auditLog.columns.action') },
  { key: 'user', label: t('auditLog.columns.user') },
  { key: 'resource_type', label: t('auditLog.columns.resource') },
  { key: 'ip_address', label: t('auditLog.columns.ipAddress') },
  { key: 'details', label: t('auditLog.columns.details') },
  { key: 'created_at', label: t('auditLog.columns.created') },
]

const selectedAction = ref('__all__')

const { items, total, isLoading, totalPages, pagination, goToPage, setPageSize } =
  useDataTable<AuditLogOut>({
    fetcher: (params) =>
      auditLogsStore.list({
        page_number: params.page_number,
        page_size: params.page_size,
        ...(selectedAction.value !== '__all__' ? { action: selectedAction.value } : {}),
      }),
  })

watch(selectedAction, () => goToPage(1))

function formatDetailValue(val: unknown): string {
  if (val === null || val === undefined) return '-'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}
</script>
