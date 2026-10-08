<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('users.form.editTitle') }}</DialogTitle>
        <DialogDescription>{{ $t('users.form.editDescription') }}</DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label>{{ $t('common.name') }}</Label>
          <Input
            v-model="form.name"
            :placeholder="$t('users.form.namePlaceholder')"
            :disabled="isLoading"
          />
          <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
        </div>
        <div class="space-y-2">
          <Label>{{ $t('common.email') }}</Label>
          <!-- The member's login across all their orgs; only they can change it. -->
          <Input :model-value="user?.email ?? ''" type="text" disabled />
          <p class="text-xs text-muted-foreground">{{ $t('users.form.emailManagedByUser') }}</p>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            :disabled="isLoading"
            @click="$emit('update:open', false)"
          >
            {{ $t('common.cancel') }}
          </Button>
          <Button type="submit" :disabled="isLoading || !isDirty || !form.name.trim()">
            <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('common.saveChanges') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2 } from '@lucide/vue'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/foundation/components/ui/dialog'
import { Button } from '@/foundation/components/ui/button'
import { Input } from '@/foundation/components/ui/input'
import { Label } from '@/foundation/components/ui/label'
import { useToast } from '@/foundation/components/ui/toast/use-toast'
import { useUsersStore } from '@/foundation/stores/users'
import { useErrorHandler } from '@/foundation/composables/useErrorHandler'
import { useValidation } from '@/foundation/composables/useValidation'
import { useRules } from '@/foundation/composables/useRules'
import type { UserOut } from '@/foundation/types'

const props = defineProps<{
  open: boolean
  user?: UserOut | null
}>()

const emit = defineEmits<{
  'update:open': [value: boolean]
  saved: []
}>()

const { t } = useI18n()
const { toast } = useToast()
const usersStore = useUsersStore()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const rules = useRules()
const { form, errors, validate, clearErrors } = useValidation({
  name: rules.required,
})

const isLoading = ref(false)
const errorMessage = ref('')
const baseline = reactive({ name: '' })

const isDirty = computed(() => form.name !== baseline.name)

watch(
  [() => props.open, () => props.user],
  ([open]) => {
    if (!open) return
    form.name = props.user?.name ?? ''
    baseline.name = form.name
    clearErrors()
    errorMessage.value = ''
  },
  { immediate: true },
)

async function onSubmit() {
  if (!validate() || !props.user) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await usersStore.patch(props.user.id, { name: form.name })
    toast({ title: t('users.form.saved') })
    emit('update:open', false)
    emit('saved')
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    if (fieldErrors['body__name']) {
      errors.name = fieldErrors['body__name']
    } else {
      errorMessage.value = resolveError(err)
    }
  } finally {
    isLoading.value = false
  }
}
</script>
