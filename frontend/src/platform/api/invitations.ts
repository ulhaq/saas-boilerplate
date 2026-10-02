import { api } from './client'

export const invitationsApi = {
  list() {
    return api.get('/invitations')
  },

  revoke(id: number) {
    return api.delete('/invitations/{invitation_id}', { path: { invitation_id: id } })
  },
}
