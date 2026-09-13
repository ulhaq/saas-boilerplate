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
          <Input
            v-model="form.email"
            type="text"
            :placeholder="$t('users.form.emailPlaceholder')"
            :disabled="isLoading"
          />
          <p v-if="errors.email" class="text-xs text-destructive">{{ errors.email }}</p>
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
          <Button
            type="submit"
            :disabled="isLoading || !isDirty || !form.name.trim() || !form.email.trim()"
          >
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
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { useToast } from '@/platform/components/ui/toast/use-toast'
import { useUsersStore } from '@/platform/stores/users'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import type { UserOut } from '@/platform/types'

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
  email: rules.email,
})

const isLoading = ref(false)
const errorMessage = ref('')
const baseline = reactive({ name: '', email: '' })

const isDirty = computed(() => form.name !== baseline.name || form.email !== baseline.email)

watch(
  [() => props.open, () => props.user],
  ([open]) => {
    if (!open) return
    form.name = props.user?.name ?? ''
    form.email = props.user?.email ?? ''
    baseline.name = form.name
    baseline.email = form.email
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
    await usersStore.patch(props.user.id, { name: form.name, email: form.email })
    toast({ title: t('users.form.saved') })
    emit('update:open', false)
    emit('saved')
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    if (fieldErrors['body__email']) {
      errors.email = fieldErrors['body__email']
    } else if (fieldErrors['body__name']) {
      errors.name = fieldErrors['body__name']
    } else {
      errorMessage.value = resolveError(err)
    }
  } finally {
    isLoading.value = false
  }
}
</script>
