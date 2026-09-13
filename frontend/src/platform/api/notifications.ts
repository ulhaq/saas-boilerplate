import { apiClient } from './client'
import type { NotificationOut, UnreadCountOut } from '@/platform/types/notification'
import type { PaginatedResponse } from '@/platform/types'

export const notificationsApi = {
  list(params?: { page_number?: number; page_size?: number }) {
    return apiClient.get<PaginatedResponse<NotificationOut>>('/notifications', { params })
  },

  unreadCount() {
    return apiClient.get<UnreadCountOut>('/notifications/unread-count')
  },

  markRead(id: number) {
    return apiClient.post<NotificationOut>(`/notifications/${id}/read`)
  },

  markAllRead() {
    return apiClient.post('/notifications/read-all')
  },
}
