import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsApi } from '@/foundation/api/notifications'
import { useRealtimeStore } from '@/foundation/stores/realtime'
import type {
  NotificationOut,
  NotificationPreferenceIn,
  NotificationPreferenceOut,
} from '@/foundation/types/notification'
import type { PaginatedResponse } from '@/foundation/types'

type ListParams = Record<string, string | number | undefined>

// Realtime events (`NotificationEvent` in the backend) that change the unread count.
const UNREAD_COUNT_EVENTS = ['notification.created', 'notification.read']

export const useNotificationsStore = defineStore('notifications', () => {
  const realtime = useRealtimeStore()
  const notifications = ref<NotificationOut[]>([])
  const total = ref(0)
  const unreadCount = ref(0)
  const isLoading = ref(false)
  // The user's per-category channel choices (settings page).
  const preferences = ref<NotificationPreferenceOut[]>([])
  let unsubscribers: Array<() => void> = []
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
      // silent - a background refresh should not surface errors
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

  async function fetchPreferences() {
    const { data } = await notificationsApi.preferences()
    preferences.value = data
  }

  async function updatePreferences(changes: NotificationPreferenceIn[]) {
    const { data } = await notificationsApi.updatePreferences(changes)
    preferences.value = data
  }

  // Keep the unread count current: fetch it now, whenever the realtime stream
  // (re)connects, and when an event says it changed (e.g. read in another tab).
  function start() {
    if (unsubscribers.length) return
    fetchUnreadCount()
    unsubscribers = [
      realtime.onSync(fetchUnreadCount),
      ...UNREAD_COUNT_EVENTS.map((type) => realtime.on(type, fetchUnreadCount)),
    ]
  }

  function stop() {
    for (const unsubscribe of unsubscribers) unsubscribe()
    unsubscribers = []
  }

  function clear() {
    notifications.value = []
    total.value = 0
    unreadCount.value = 0
    preferences.value = []
    stop()
  }

  return {
    notifications,
    total,
    unreadCount,
    isLoading,
    preferences,
    hasUnread,
    onNewNotifications,
    fetchUnreadCount,
    fetchNotifications,
    list,
    markRead,
    markAllRead,
    fetchPreferences,
    updatePreferences,
    start,
    stop,
    clear,
  }
})
