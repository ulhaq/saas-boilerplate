import { defineStore } from 'pinia'
import { ref } from 'vue'
import { invitationsApi } from '@/platform/api/invitations'
import { usersApi } from '@/platform/api/users'
import type { InvitationOut } from '@/platform/types'

// Pending invitations of the active organization (admin surface).
export const useInvitationsStore = defineStore('invitations', () => {
  const invitations = ref<InvitationOut[]>([])

  async function fetchInvitations(): Promise<void> {
    const { data } = await invitationsApi.list()
    invitations.value = data
  }

  async function revoke(id: number): Promise<void> {
    await invitationsApi.revoke(id)
    invitations.value = invitations.value.filter((i) => i.id !== id)
  }

  // Re-inviting replaces the pending invite server-side: new link, fresh
  // expiry, old link stops working. Deleted roles are dropped.
  async function resend(invitation: InvitationOut): Promise<void> {
    await usersApi.invite({
      email: invitation.email,
      role_ids: invitation.roles.map((r) => r.id),
    })
    await fetchInvitations()
  }

  function clear(): void {
    invitations.value = []
  }

  return { invitations, fetchInvitations, revoke, resend, clear }
})
