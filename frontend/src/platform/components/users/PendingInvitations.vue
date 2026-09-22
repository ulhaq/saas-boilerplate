<template>
  <section v-if="store.invitations.length" class="mt-8 animate-fade-in">
    <div class="mb-3">
      <h2 class="text-sm font-semibold">
        {{ $t('users.pendingInvitations.title') }}
        <span class="ml-1 text-muted-foreground font-normal">
          ({{ store.invitations.length }})
        </span>
      </h2>
      <p class="text-xs text-muted-foreground">
        {{ $t('users.pendingInvitations.description') }}
      </p>
    </div>

    <DataTable
      :columns="columns"
      :items="store.invitations"
      :total="store.invitations.length"
      :show-pagination="false"
      :row-class="(inv) => (inv.is_expired ? 'opacity-60' : undefined)"
    >
      <template #row="{ item: inv }">
        <TableCell class="font-medium text-sm">{{ inv.email }}</TableCell>
        <TableCell>
          <div class="flex flex-wrap gap-1">
            <Badge
              v-for="role in inv.roles.slice(0, BADGE_MAX)"
              :key="role.id"
              variant="secondary"
              class="text-xs"
            >
              {{ role.name }}
            </Badge>
            <Badge v-if="inv.roles.length > BADGE_MAX" variant="outline" class="text-xs">
              +{{ inv.roles.length - BADGE_MAX }}
            </Badge>
            <Badge v-if="!inv.roles.length" variant="warning" class="text-xs">
              {{ $t('users.noRoles') }}
            </Badge>
          </div>
        </TableCell>
        <TableCell class="text-xs text-muted-foreground">
          {{ inv.invited_by?.name ?? $t('users.pendingInvitations.deletedUser') }}
        </TableCell>
        <TableCell class="text-xs text-muted-foreground">
          <span v-if="inv.is_expired" class="inline-flex items-center gap-1.5">
            {{ formatDate(inv.expires_at) }}
            <Badge variant="destructive" class="text-[10px] px-1 py-0">
              {{ $t('users.pendingInvitations.expired') }}
            </Badge>
          </span>
          <span v-else>{{ formatDate(inv.expires_at) }}</span>
        </TableCell>
      </template>
      <template #actions="{ item: inv }">
        <div class="flex justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            class="h-7 text-xs"
            :disabled="busyId === inv.id"
            @click="handleResend(inv)"
          >
            <Loader2
              v-if="busyId === inv.id && busyAction === 'resend'"
              class="w-3 h-3 mr-1 animate-spin"
            />
            <RotateCw v-else class="w-3 h-3 mr-1" />
            {{ $t('users.pendingInvitations.resend') }}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="h-7 text-xs text-destructive hover:text-destructive hover:bg-destructive/10"
            :disabled="busyId === inv.id"
            @click="handleRevoke(inv)"
          >
            <Loader2
              v-if="busyId === inv.id && busyAction === 'revoke'"
              class="w-3 h-3 mr-1 animate-spin"
            />
            {{ $t('users.pendingInvitations.revoke') }}
          </Button>
        </div>
      </template>
    </DataTable>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, RotateCw } from 'lucide-vue-next'
import { Badge } from '@/platform/components/ui/badge'
import { Button } from '@/platform/components/ui/button'
import { TableCell } from '@/platform/components/ui/table'
import DataTable from '@/platform/components/common/DataTable.vue'
import { useInvitationsStore } from '@/platform/stores/invitations'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { BADGE_MAX } from '@/platform/constants'
import type { InvitationOut } from '@/platform/types'

// Pending invitations of the active org, shown under the member list. Hidden
// when there are none. Render only for users with manage:organization_user.
const { t } = useI18n()
const store = useInvitationsStore()
const { confirm } = useConfirm()
const { toast } = useToast()
const { handleError } = useErrorHandler()
const { formatDate } = useFormatDate()

const columns = [
  { key: 'email', label: t('common.email') },
  { key: 'roles', label: t('users.columns.roles') },
  { key: 'invited_by', label: t('users.pendingInvitations.invitedBy') },
  { key: 'expires_at', label: t('users.pendingInvitations.expires') },
]

const busyId = ref<number | null>(null)
const busyAction = ref<'resend' | 'revoke' | null>(null)

async function run(inv: InvitationOut, action: 'resend' | 'revoke', fn: () => Promise<void>) {
  busyId.value = inv.id
  busyAction.value = action
  try {
    await fn()
  } finally {
    busyId.value = null
    busyAction.value = null
  }
}

async function handleResend(inv: InvitationOut) {
  await run(inv, 'resend', async () => {
    try {
      await store.resend(inv)
      toast({
        title: t('users.pendingInvitations.resent'),
        description: t('users.invite.sentDescription', { email: inv.email }),
      })
    } catch (err: unknown) {
      handleError(err, t('users.pendingInvitations.resendFailed'))
    }
  })
}

async function handleRevoke(inv: InvitationOut) {
  const ok = await confirm(
    t('users.pendingInvitations.revokeTitle'),
    t('users.pendingInvitations.revokeDescription', { email: inv.email }),
    t('users.pendingInvitations.revoke'),
  )
  if (!ok) return
  await run(inv, 'revoke', async () => {
    try {
      await store.revoke(inv.id)
      toast({ title: t('users.pendingInvitations.revoked') })
    } catch (err: unknown) {
      handleError(err, t('users.pendingInvitations.revokeFailed'))
    }
  })
}

onMounted(async () => {
  // Drop any list from a previous org/session before showing this one.
  store.clear()
  try {
    await store.fetchInvitations()
  } catch (err: unknown) {
    handleError(err, t('users.pendingInvitations.loadFailed'))
  }
})
</script>
