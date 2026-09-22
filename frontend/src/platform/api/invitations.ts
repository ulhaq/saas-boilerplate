import { apiClient } from './client'
import type { InvitationOut } from '@/platform/types'

export const invitationsApi = {
  list() {
    return apiClient.get<InvitationOut[]>('/invitations')
  },

  revoke(id: number) {
    return apiClient.delete(`/invitations/${id}`)
  },
}
