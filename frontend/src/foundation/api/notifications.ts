import { api } from './client'
import type { NotificationPreferenceIn } from '@/foundation/types/notification'

export const notificationsApi = {
  list(params?: { page_number?: number; page_size?: number }) {
    return api.get('/notifications', { query: params })
  },

  unreadCount() {
    return api.get('/notifications/unread-count')
  },

  markRead(id: number) {
    return api.post('/notifications/{notification_id}/read', {
      path: { notification_id: id },
    })
  },

  markAllRead() {
    return api.post('/notifications/read-all')
  },

  preferences() {
    return api.get('/notifications/preferences')
  },

  updatePreferences(preferences: NotificationPreferenceIn[]) {
    return api.patch('/notifications/preferences', { body: preferences })
  },
}
