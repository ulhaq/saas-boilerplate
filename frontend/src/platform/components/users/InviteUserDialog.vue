<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('users.invite.dialogTitle') }}</DialogTitle>
        <DialogDescription>{{ $t('users.invite.dialogDescription') }}</DialogDescription>
      </DialogHeader>

      <!-- Limit reached state -->
      <PlanLimitReached
        v-if="limitReached"
        :title="$t('users.invite.limitReachedTitle')"
        :description="
          $t('users.invite.limitReachedDescription', { limit: subscriptionStore.seatLimit })
        "
        @dismiss="$emit('update:open', false)"
      />

      <!-- Normal invite form -->
      <form v-else class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="invite-email">{{ $t('common.email') }}</Label>
          <Input
            id="invite-email"
            v-model="form.email"
            type="text"
            :placeholder="$t('users.form.emailPlaceholder')"
            :disabled="isLoading"
            autofocus
          />
          <p v-if="errors.email" class="text-xs text-destructive">{{ errors.email }}</p>
        </div>

        <div class="space-y-2">
          <Label>{{ $t('users.invite.roles') }}</Label>
          <div v-if="loadingRoles" class="py-2 space-y-2">
            <Skeleton v-for="n in 3" :key="n" class="h-9 w-full" />
          </div>
          <div v-else class="space-y-1 max-h-48 overflow-y-auto">
            <div
              v-for="role in availableRoles"
              :key="role.id"
              class="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted cursor-pointer"
              @click="toggleRole(role.id)"
            >
              <Checkbox
                :model-value="selectedRoleIds.includes(role.id)"
                @click.stop="toggleRole(role.id)"
              />
              <div>
                <p class="text-sm font-medium">{{ role.name }}</p>
                <p v-if="role.description" class="text-xs text-muted-foreground">
                  {{ role.description }}
                </p>
              </div>
            </div>
            <div v-if="!availableRoles.length" class="px-3 py-2">
              <PermissionGuard permission="create:role">
                <Button type="button" variant="outline" size="sm" @click="showRoleForm = true">
                  <Plus class="w-4 h-4 mr-2" />
                  {{ $t('roles.addRole') }}
                </Button>
              </PermissionGuard>
            </div>
          </div>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            :disabled="isLoading"
            @click="$emit('update:open', false)"
            >{{ $t('common.cancel') }}</Button
          >
          <Button
            type="submit"
            :disabled="isLoading || !form.email.trim() || selectedRoleIds.length === 0"
          >
            <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('users.invite.send') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>

  <RoleForm v-model:open="showRoleForm" @saved="onRoleCreated" />
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, Plus } from 'lucide-vue-next'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/platform/components/ui/dialog'
import { Button } from '@/platform/components/ui/button'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Checkbox } from '@/platform/components/ui/checkbox'
import { Skeleton } from '@/platform/components/ui/skeleton'
import PermissionGuard from '@/platform/components/common/PermissionGuard.vue'
import RoleForm from '@/platform/components/roles/RoleForm.vue'
import { useUsersStore } from '@/platform/stores/users'
import { useRolesStore } from '@/platform/stores/roles'
import { PAGE_SIZE } from '@/platform/constants'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import type { RoleOut } from '@/platform/types'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [boolean]; invited: [] }>()

const { t } = useI18n()
const { toast } = useToast()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const subscriptionStore = useSubscriptionStore()
const usersStore = useUsersStore()
const rolesStore = useRolesStore()

const rules = useRules()
const { form, errors, validate, clearErrors } = useValidation({ email: rules.email })
const errorMessage = ref('')
const isLoading = ref(false)
const limitReached = ref(false)

const availableRoles = ref<RoleOut[]>([])
const selectedRoleIds = ref<number[]>([])
const loadingRoles = ref(false)
const showRoleForm = ref(false)

async function loadRoles() {
  loadingRoles.value = true
  try {
    const data = await rolesStore.list({ page_size: PAGE_SIZE })
    availableRoles.value = data.items.filter((r) => !(r.is_protected && r.name === 'Owner'))
  } finally {
    loadingRoles.value = false
  }
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      limitReached.value = false
      return
    }
    form.email = ''
    clearErrors()
    errorMessage.value = ''
    selectedRoleIds.value = []
    await loadRoles()
  },
)

async function onRoleCreated(role: RoleOut | null) {
  await loadRoles()
  if (role) selectedRoleIds.value = [role.id]
}

function toggleRole(id: number) {
  const idx = selectedRoleIds.value.indexOf(id)
  if (idx >= 0) selectedRoleIds.value.splice(idx, 1)
  else selectedRoleIds.value.push(id)
}

function isCapacityExceeded(err: unknown): boolean {
  const e = err as { isAxiosError?: boolean; response?: { data?: { error_code?: string } } }
  return e?.isAxiosError === true && e?.response?.data?.error_code === 'capacity_exceeded'
}

async function onSubmit() {
  if (!validate()) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await usersStore.invite({ email: form.email.trim(), role_ids: selectedRoleIds.value })
    emit('update:open', false)
    emit('invited')
    toast({
      title: t('users.invite.sent'),
      description: `${t('users.invite.sentDescription', { email: form.email.trim() })} ${t('common.checkSpam')}`,
    })
  } catch (err: unknown) {
    if (isCapacityExceeded(err)) {
      limitReached.value = true
    } else {
      const fieldErrors = resolveFieldErrors(err)
      if (fieldErrors['body__email']) {
        errors.email = fieldErrors['body__email']
      } else {
        errorMessage.value = resolveError(err)
      }
    }
  } finally {
    isLoading.value = false
  }
}
</script>
