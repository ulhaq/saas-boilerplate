<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('organizations.transferOwnershipDialog.title') }}</DialogTitle>
        <DialogDescription>{{
          $t('organizations.transferOwnershipDialog.description', { name: organization?.name })
        }}</DialogDescription>
      </DialogHeader>

      <div v-if="loading" class="py-4 space-y-2">
        <Skeleton v-for="n in 3" :key="n" class="h-12 w-full" />
      </div>
      <div v-else class="space-y-1 max-h-72 overflow-y-auto py-1">
        <div
          v-for="user in candidates"
          :key="user.id"
          :class="[
            'flex items-center gap-3 px-3 py-2 rounded-md cursor-pointer transition-colors',
            selectedUserId === user.id ? 'bg-primary/10 ring-1 ring-primary' : 'hover:bg-muted',
          ]"
          @click="selectedUserId = user.id"
        >
          <div
            class="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0"
          >
            <span class="text-xs font-medium text-primary">{{ initials(user.name) }}</span>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate">{{ user.name }}</p>
            <p class="text-xs text-muted-foreground truncate">{{ user.email }}</p>
          </div>
        </div>
        <EmptyState
          v-if="!candidates.length"
          :title="$t('organizations.transferOwnershipDialog.noMembers')"
          :description="$t('organizations.transferOwnershipDialog.noMembersDescription')"
        />
      </div>

      <DialogFooter>
        <Button variant="outline" @click="$emit('update:open', false)">{{
          $t('common.cancel')
        }}</Button>
        <Button variant="destructive" :disabled="!selectedUserId || saving" @click="submit">
          <Loader2 v-if="saving" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('organizations.transferOwnershipDialog.confirm') }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2 } from 'lucide-vue-next'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/platform/components/ui/dialog'
import { Button } from '@/platform/components/ui/button'
import { Skeleton } from '@/platform/components/ui/skeleton'
import EmptyState from '@/platform/components/common/EmptyState.vue'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useProfileStore } from '@/platform/stores/profile'
import type { OrganizationOut, UserOut } from '@/platform/types'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'

const props = defineProps<{ open: boolean; organization?: OrganizationOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const { toast } = useToast()
const { handleError } = useErrorHandler()
const { t } = useI18n()
const profile = useProfileStore()
const organizationsStore = useOrganizationsStore()

const loading = ref(false)
const saving = ref(false)
const candidates = ref<UserOut[]>([])
const selectedUserId = ref<number | null>(null)

watch(
  () => props.open,
  async (open) => {
    if (!open || !props.organization) return
    selectedUserId.value = null
    loading.value = true
    try {
      const data = await organizationsStore.getUsers(props.organization.id)
      candidates.value = data.items.filter((u) => u.id !== profile.user?.id)
    } finally {
      loading.value = false
    }
  },
)

async function submit() {
  if (!props.organization || !selectedUserId.value) return
  saving.value = true
  try {
    await organizationsStore.transferOwnership(props.organization.id, selectedUserId.value)
    const newOwner = candidates.value.find((u) => u.id === selectedUserId.value)
    toast({
      title: t('organizations.transferOwnershipDialog.success', { name: newOwner?.name ?? '' }),
    })
    emit('update:open', false)
    emit('saved')
  } catch (err: unknown) {
    handleError(err, t('organizations.transferOwnershipDialog.failed'))
  } finally {
    saving.value = false
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
</script>
