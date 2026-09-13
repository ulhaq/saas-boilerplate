<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('users.roleDialog.title') }}</DialogTitle>
        <DialogDescription>{{
          $t('users.roleDialog.description', { name: user?.name })
        }}</DialogDescription>
      </DialogHeader>

      <div v-if="loadingRoles" class="py-4 space-y-2">
        <Skeleton v-for="n in 3" :key="n" class="h-10 w-full" />
      </div>
      <div v-else class="space-y-2 max-h-64 overflow-y-auto py-1">
        <div
          v-for="role in availableRoles"
          :key="role.id"
          class="flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted cursor-pointer"
          @click="toggleRole(role.id)"
        >
          <Checkbox
            :model-value="selectedIds.includes(role.id)"
            @click.stop="toggleRole(role.id)"
          />
          <div>
            <p class="text-sm font-medium">{{ role.name }}</p>
            <p v-if="role.description" class="text-xs text-muted-foreground">
              {{ role.description }}
            </p>
          </div>
        </div>
        <EmptyState
          v-if="!availableRoles.length"
          :title="$t('users.roleDialog.noRoles')"
          :description="$t('users.roleDialog.createRolesFirst')"
        >
          <PermissionGuard permission="create:role">
            <Button
              type="button"
              variant="outline"
              size="sm"
              class="mt-4"
              @click="showRoleForm = true"
            >
              <Plus class="w-4 h-4 mr-2" />
              {{ $t('roles.addRole') }}
            </Button>
          </PermissionGuard>
        </EmptyState>
      </div>

      <DialogFooter>
        <Button variant="outline" :disabled="isLoading" @click="$emit('update:open', false)">{{
          $t('common.cancel')
        }}</Button>
        <Button :disabled="isLoading || !isDirty" @click="onSave">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('common.save') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>

  <RoleForm v-model:open="showRoleForm" @saved="onRoleCreated" />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, Plus } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/platform/components/ui/dialog'
import { Button } from '@/platform/components/ui/button'
import { Checkbox } from '@/platform/components/ui/checkbox'
import { Skeleton } from '@/platform/components/ui/skeleton'
import EmptyState from '@/platform/components/common/EmptyState.vue'
import PermissionGuard from '@/platform/components/common/PermissionGuard.vue'
import RoleForm from '@/platform/components/roles/RoleForm.vue'
import { useUsersStore } from '@/platform/stores/users'
import { useRolesStore } from '@/platform/stores/roles'
import { PAGE_SIZE } from '@/platform/constants'
import type { UserOut, RoleOut } from '@/platform/types'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'

const props = defineProps<{ open: boolean; user?: UserOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const { toast } = useToast()
const { handleError } = useErrorHandler()
const { t } = useI18n()
const usersStore = useUsersStore()
const rolesStore = useRolesStore()
const availableRoles = ref<RoleOut[]>([])
const selectedIds = ref<number[]>([])
const baseline = ref<number[]>([])
const loadingRoles = ref(false)
const isLoading = ref(false)
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

const isDirty = computed(() => {
  if (selectedIds.value.length !== baseline.value.length) return true
  const base = new Set(baseline.value)
  return selectedIds.value.some((id) => !base.has(id))
})

watch(
  () => props.open,
  async (open) => {
    if (!open || !props.user) return
    selectedIds.value = props.user.roles.map((r) => r.id)
    baseline.value = [...selectedIds.value]
    await loadRoles()
  },
)

async function onRoleCreated(role: RoleOut | null) {
  await loadRoles()
  if (role && !selectedIds.value.includes(role.id)) selectedIds.value.push(role.id)
}

function toggleRole(id: number) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

async function onSave() {
  if (!props.user) return
  isLoading.value = true
  try {
    await usersStore.setRoles(props.user.id, { role_ids: selectedIds.value })
    emit('update:open', false)
    emit('saved')
    toast({ title: t('users.roleDialog.saved') })
  } catch (err: unknown) {
    handleError(err, t('users.roleDialog.saveFailed'))
  } finally {
    isLoading.value = false
  }
}
</script>
