<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  breadcrumb: nav.notifications
</route>

<template>
  <div class="animate-fade-in">
    <PageHeader :title="$t('notifications.title')">
      <template #actions>
        <Button
          v-if="items.some((n) => !n.read_at)"
          variant="outline"
          size="sm"
          @click="handleMarkAllRead"
        >
          {{ $t('notifications.markAllRead') }}
        </Button>
      </template>
    </PageHeader>

    <DataTable
      :columns="columns"
      :items="items"
      :total="total"
      :page="pagination.page"
      :page-size="pagination.pageSize"
      :total-pages="totalPages"
      :loading="isLoading"
      :empty-title="$t('notifications.empty')"
      :row-class="(item) => (!item.read_at ? 'bg-primary/[0.04]' : undefined)"
      :on-row-click="handleRowClick"
      @update:page="goToPage"
      @update:page-size="setPageSize"
    >
      <template #row="{ item }">
        <TableCell class="relative">
          <!-- unread accent rail -->
          <span v-if="!item.read_at" class="absolute inset-y-0 left-0 w-1 bg-primary" />
          <div class="flex items-start gap-3">
            <!-- avatar / icon medallion -->
            <div
              class="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-xs font-semibold text-muted-foreground ring-1 ring-inset ring-foreground/5 transition-colors group-hover:text-foreground"
              :class="{ 'opacity-70': item.read_at }"
            >
              <span v-if="getAvatarSeed(item)">{{ initials(getAvatarSeed(item)!) }}</span>
              <Bell v-else class="h-4 w-4" />
            </div>
            <div class="min-w-0">
              <p
                class="truncate text-sm font-medium"
                :class="{ 'font-normal text-muted-foreground': item.read_at }"
              >
                {{ getTitle(item) }}
              </p>
              <div
                v-if="getCategories(item).length"
                class="mt-1.5 flex flex-wrap items-center gap-1"
              >
                <span
                  v-for="cat in getCategories(item)"
                  :key="cat"
                  class="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium"
                  :class="[getCategoryBadgeClass(item, cat), { 'opacity-70': item.read_at }]"
                >
                  <span class="h-1.5 w-1.5 rounded-full" :class="getCategoryDotClass(item, cat)" />
                  {{ getCategoryLabel(item, cat) }}
                </span>
              </div>
              <p v-else-if="getDescription(item)" class="mt-0.5 text-xs text-muted-foreground">
                {{ getDescription(item) }}
              </p>
            </div>
          </div>
        </TableCell>
        <TableCell
          class="whitespace-nowrap text-right align-top text-sm text-muted-foreground"
          :title="formatDateTime(item.created_at)"
        >
          {{ formatRelativeTime(item.created_at) }}
        </TableCell>
      </template>
      <template #actions="{ item }">
        <div class="flex justify-center">
          <button
            v-if="!item.read_at"
            class="relative flex h-5 w-5 items-center justify-center rounded transition-all hover:bg-primary/10"
            :title="$t('notifications.markRead')"
            @click="handleMarkRead(item)"
          >
            <span
              class="absolute h-2 w-2 rounded-full bg-primary transition-opacity group-hover:opacity-0"
            />
            <Check
              :stroke-width="3"
              class="h-4 w-4 text-primary opacity-0 transition-opacity group-hover:opacity-100"
            />
          </button>
          <div v-else class="h-5 w-5" />
        </div>
      </template>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Bell, Check } from 'lucide-vue-next'
import { TableCell } from '@/platform/components/ui/table'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import DataTable from '@/platform/components/common/DataTable.vue'
import Button from '@/platform/components/ui/button/Button.vue'
import { useDataTable } from '@/platform/composables/useDataTable'
import { useNotificationPresenter } from '@/platform/composables/useNotificationPresenter'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { useNotificationsStore } from '@/platform/stores/notifications'
import { initials } from '@/platform/utils/initials'
import type { NotificationOut } from '@/platform/types/notification'

const { t } = useI18n()
const router = useRouter()
const notificationsStore = useNotificationsStore()
const {
  getTitle,
  getDescription,
  getRoute,
  getCategories,
  getAvatarSeed,
  getCategoryLabel,
  getCategoryBadgeClass,
  getCategoryDotClass,
} = useNotificationPresenter()
const { formatRelativeTime, formatDateTime } = useFormatDate()

const columns = [
  { key: 'content', label: t('notifications.title') },
  { key: 'created_at', label: t('common.date') },
]

const { items, total, isLoading, pagination, totalPages, goToPage, setPageSize, refresh } =
  useDataTable<NotificationOut>({ fetcher: notificationsStore.list })

async function handleMarkRead(n: NotificationOut) {
  await notificationsStore.markRead(n.id)
  refresh()
}

function handleRowClick(n: NotificationOut) {
  const route = getRoute(n)
  if (route) {
    if (!n.read_at) notificationsStore.markRead(n.id)
    router.push(route)
  } else if (!n.read_at) {
    handleMarkRead(n)
  }
}

async function handleMarkAllRead() {
  await notificationsStore.markAllRead()
  refresh()
}
</script>
