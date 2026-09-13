import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsApi } from '@/platform/api/notifications'
import type { NotificationOut } from '@/platform/types/notification'
import type { PaginatedResponse } from '@/platform/types'

type ListParams = Record<string, string | number | undefined>

const POLL_INTERVAL_MS = 60_000

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref<NotificationOut[]>([])
  const total = ref(0)
  const unreadCount = ref(0)
  const isLoading = ref(false)
  let pollTimer: ReturnType<typeof setInterval> | null = null
  let onNewNotificationsCallback: ((delta: number) => void) | null = null

  const hasUnread = computed(() => unreadCount.value > 0)

  function onNewNotifications(cb: (delta: number) => void) {
    onNewNotificationsCallback = cb
  }

  async function fetchUnreadCount() {
    try {
      const { data: unread } = await notificationsApi.unreadCount()
      const prev = unreadCount.value
      unreadCount.value = unread.count
      if (unread.count > prev && onNewNotificationsCallback) {
        onNewNotificationsCallback(unread.count - prev)
      }
    } catch {
      // silent - polling should not surface errors
    }
  }

  async function fetchNotifications(page_number = 1, page_size = 20) {
    isLoading.value = true
    try {
      const { data: page } = await notificationsApi.list({ page_number, page_size })
      notifications.value = page.items
      total.value = page.total
    } finally {
      isLoading.value = false
    }
  }

  // Passthrough for the notifications table (useDataTable), separate from the
  // bell's cached feed state above.
  async function list(params: ListParams = {}): Promise<PaginatedResponse<NotificationOut>> {
    const { data: page } = await notificationsApi.list(params)
    return page
  }

  async function markRead(id: number) {
    const { data: updated } = await notificationsApi.markRead(id)
    const idx = notifications.value.findIndex((n) => n.id === id)
    if (idx !== -1) notifications.value[idx] = updated
    unreadCount.value = Math.max(0, unreadCount.value - 1)
  }

  async function markAllRead() {
    await notificationsApi.markAllRead()
    notifications.value = notifications.value.map((n) => ({
      ...n,
      read_at: n.read_at ?? new Date().toISOString(),
    }))
    unreadCount.value = 0
  }

  function startPolling() {
    if (pollTimer) return
    fetchUnreadCount()
    pollTimer = setInterval(fetchUnreadCount, POLL_INTERVAL_MS)
  }

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  function clear() {
    notifications.value = []
    total.value = 0
    unreadCount.value = 0
    stopPolling()
  }

  return {
    notifications,
    total,
    unreadCount,
    isLoading,
    hasUnread,
    onNewNotifications,
    fetchUnreadCount,
    fetchNotifications,
    list,
    markRead,
    markAllRead,
    startPolling,
    stopPolling,
    clear,
  }
})
