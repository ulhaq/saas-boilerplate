<route lang="yaml">
meta:
  breadcrumb: settings.general
</route>

<template>
  <div class="max-w-2xl animate-fade-in">
    <PageHeader :title="$t('settings.thisOrganization')" :description="orgIdLabel" />

    <Card v-if="canEdit" class="mt-6">
      <CardHeader>
        <CardTitle class="text-base">{{ $t('settings.organizationDetails') }}</CardTitle>
        <p class="text-sm text-muted-foreground">
          {{ $t('settings.organizationDetailsDescription') }}
        </p>
      </CardHeader>
      <CardContent>
        <form class="space-y-4" @submit.prevent="saveDetails">
          <div class="space-y-2">
            <Label>{{ $t('settings.organizationName') }}</Label>
            <Input v-model="form.name" :disabled="saving" />
            <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
          </div>
          <SaveButton :saving="saving" :saved="detailsSaved" :disabled="!isDirty">
            {{ $t('common.saveChanges') }}
          </SaveButton>
        </form>
      </CardContent>
    </Card>

    <Card v-if="canViewMembers" class="mt-6">
      <CardHeader>
        <CardTitle class="text-base">{{ $t('settings.members') }}</CardTitle>
        <p class="text-sm text-muted-foreground">{{ $t('settings.membersDescription') }}</p>
      </CardHeader>
      <CardContent>
        <div v-if="membersLoading" class="space-y-2">
          <Skeleton v-for="n in 3" :key="n" class="h-12 w-full" />
        </div>
        <div v-else class="space-y-1">
          <div
            v-for="member in members"
            :key="member.id"
            class="flex items-center justify-between px-3 py-2 rounded-md hover:bg-muted"
          >
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <span class="text-xs font-medium text-primary">{{ initials(member.name) }}</span>
              </div>
              <div>
                <p class="text-sm font-medium">{{ member.name }}</p>
                <p class="text-xs text-muted-foreground">{{ member.email }}</p>
              </div>
            </div>
            <PermissionGuard permission="manage:organization_user">
              <Button
                variant="ghost"
                size="sm"
                class="text-destructive hover:text-destructive hover:bg-destructive/10 h-7 w-7 p-0"
                @click="removeMember(member)"
              >
                <X class="w-4 h-4" />
              </Button>
            </PermissionGuard>
          </div>
          <EmptyState
            v-if="!members.length"
            :title="$t('organizations.usersDialog.noMembers')"
            :description="$t('organizations.usersDialog.noUsers')"
          />
        </div>
      </CardContent>
    </Card>

    <div v-if="isOwner" class="mt-8">
      <h2 class="text-sm font-semibold text-destructive uppercase tracking-wider mb-3">
        {{ $t('settings.dangerZone') }}
      </h2>
      <Card class="border-destructive/50">
        <CardContent class="pt-6 space-y-6">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="font-medium text-sm">{{ $t('organizations.transferOwnership') }}</p>
              <p class="text-sm text-muted-foreground mt-0.5">
                {{ $t('settings.transferOwnershipDescription') }}
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              class="shrink-0 w-full sm:w-auto"
              @click="showTransfer = true"
            >
              {{ $t('organizations.transferOwnership') }}
            </Button>
          </div>

          <div class="border-t" />

          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p class="font-medium text-sm">{{ $t('settings.deleteOrganization') }}</p>
              <p class="text-sm text-muted-foreground mt-0.5">
                {{ $t('settings.deleteOrganizationDescription') }}
              </p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              class="shrink-0 w-full sm:w-auto"
              :disabled="deleting"
              @click="showDeleteForm = true"
            >
              {{ $t('settings.deleteOrganization') }}
            </Button>
          </div>

          <form
            v-if="showDeleteForm"
            class="mt-4 space-y-3 border-t pt-4"
            @submit.prevent="handleDeleteOrg"
          >
            <div class="space-y-2">
              <Label for="delete-org-name">{{ $t('settings.deleteOrgConfirmLabel') }}</Label>
              <Input
                id="delete-org-name"
                v-model="deleteConfirmName"
                :placeholder="activeOrgName"
                :disabled="deleting"
                autofocus
              />
            </div>
            <p v-if="deleteError" class="text-sm text-destructive">{{ deleteError }}</p>
            <div class="flex gap-2 justify-end">
              <Button
                type="button"
                variant="outline"
                size="sm"
                :disabled="deleting"
                @click="cancelDelete"
              >
                {{ $t('common.cancel') }}
              </Button>
              <Button
                type="submit"
                variant="destructive"
                size="sm"
                :disabled="deleting || deleteConfirmName.trim() !== activeOrgName"
              >
                <Loader2 v-if="deleting" class="w-4 h-4 mr-2 animate-spin" />
                {{ $t('settings.deleteOrganization') }}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <TransferOwnershipDialog
        v-model:open="showTransfer"
        :organization="activeOrg"
        @saved="handleOwnershipTransferred"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loader2, X } from 'lucide-vue-next'
import { Card, CardHeader, CardTitle, CardContent } from '@/platform/components/ui/card'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { Skeleton } from '@/platform/components/ui/skeleton'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import EmptyState from '@/platform/components/common/EmptyState.vue'
import PermissionGuard from '@/platform/components/common/PermissionGuard.vue'
import TransferOwnershipDialog from '@/platform/components/organizations/TransferOwnershipDialog.vue'
import { useAuthStore } from '@/platform/stores/auth'
import { useSessionStore } from '@/platform/stores/session'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useUsersStore } from '@/platform/stores/users'
import { useProfileStore } from '@/platform/stores/profile'
import type { UserOut } from '@/platform/types'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { usePermission } from '@/platform/composables/usePermission'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { useFormGuard } from '@/platform/composables/useFormGuard'
import { useToast } from '@/platform/composables/useToast'
import { useSaveFeedback } from '@/platform/composables/useSaveFeedback'

const router = useRouter()
const { t } = useI18n()
const auth = useAuthStore()
const session = useSessionStore()
const orgStore = useOrganizationsStore()
const usersStore = useUsersStore()
const profile = useProfileStore()
const { confirm } = useConfirm()
const { handleError, resolveError } = useErrorHandler()
const { isOwner, hasPermission } = usePermission()
const { toast } = useToast()

const deleting = ref(false)
const { saving, saved: detailsSaved, save: saveWithFeedback } = useSaveFeedback()
const showDeleteForm = ref(false)
const showTransfer = ref(false)
const deleteConfirmName = ref('')
const deleteError = ref('')

const canEdit = computed(() => hasPermission('update:organization'))
const canViewMembers = computed(() => hasPermission('read:user'))

const members = ref<UserOut[]>([])
const membersLoading = ref(false)

const activeOrg = computed(() =>
  orgStore.organizations.find((o) => o.id === session.activeOrganizationId),
)
const activeOrgName = computed(() => activeOrg.value?.name ?? '')
const orgIdLabel = computed(() =>
  activeOrg.value ? `${t('settings.organizationId')}: ${activeOrg.value.id}` : '',
)

const rules = useRules()
const { form, errors, validate } = useValidation({ name: rules.required })

const isDirty = computed(() => form.name.trim() !== activeOrgName.value)

// Seed the form once the active organization is available (the list may still be
// loading on first render).
watch(
  activeOrgName,
  (name) => {
    if (!isDirty.value || !form.name) form.name = name
  },
  { immediate: true },
)

onMounted(() => {
  if (!orgStore.organizations.length) orgStore.fetchOrganizations().catch(() => {})
})

// Load the active org's members once we know which org is active.
watch(
  () => session.activeOrganizationId,
  async (id) => {
    if (!id || !canViewMembers.value) return
    membersLoading.value = true
    try {
      const data = await orgStore.getUsers(id)
      members.value = data.items
    } catch (err) {
      handleError(err)
    } finally {
      membersLoading.value = false
    }
  },
  { immediate: true },
)

useFormGuard(() => isDirty.value)

async function removeMember(member: UserOut) {
  const ok = await confirm(
    t('organizations.usersDialog.removeTitle'),
    t('organizations.usersDialog.removeDescription', { name: member.name }),
    t('organizations.usersDialog.removeConfirm'),
  )
  if (!ok) return
  try {
    await usersStore.removeFromOrganization(member.id)
    members.value = members.value.filter((m) => m.id !== member.id)
    toast({ title: t('organizations.usersDialog.userRemoved') })
  } catch (err) {
    handleError(err, t('organizations.usersDialog.removeFailed'))
  }
}

function initials(name: string) {
  return name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
}

async function saveDetails() {
  if (!validate() || !isDirty.value || !session.activeOrganizationId) return
  const orgId = session.activeOrganizationId
  try {
    await saveWithFeedback(async () => {
      await orgStore.patch(orgId, { name: form.name.trim() })
      // Refresh the cached list so the org switcher / topbar reflect the new name.
      await orgStore.fetchOrganizations()
    })
  } catch (err) {
    handleError(err, t('settings.failedToSaveChanges'))
  }
}

async function handleOwnershipTransferred() {
  // The current user just gave up ownership: refresh identity (drops owner role,
  // hiding the danger zone) and the cached org list.
  await profile.fetchMe()
  await orgStore.fetchOrganizations()
}

function cancelDelete() {
  showDeleteForm.value = false
  deleteConfirmName.value = ''
  deleteError.value = ''
}

async function handleDeleteOrg() {
  if (deleteConfirmName.value.trim() !== activeOrgName.value) {
    deleteError.value = t('settings.deleteOrgNameMismatch')
    return
  }

  const ok = await confirm(
    t('organizations.deleteTitle'),
    t('organizations.deleteDescription', { name: activeOrgName.value }),
    t('common.delete'),
    'destructive',
  )
  if (!ok) return

  deleting.value = true
  deleteError.value = ''
  try {
    await orgStore.remove(session.activeOrganizationId!)
    await auth.logout()
    router.push('/login')
  } catch (err) {
    deleteError.value = resolveError(err)
  } finally {
    deleting.value = false
  }
}
</script>
