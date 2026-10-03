import { api } from './client'

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
}
