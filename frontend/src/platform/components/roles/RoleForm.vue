<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{
          isEdit ? $t('roles.form.editTitle') : $t('roles.form.createTitle')
        }}</DialogTitle>
        <DialogDescription>
          {{ isEdit ? $t('roles.form.editDescription') : $t('roles.form.createDescription') }}
        </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label>{{ $t('common.name') }}</Label>
          <Input
            v-model="form.name"
            :placeholder="$t('roles.form.namePlaceholder')"
            :disabled="isLoading"
          />
          <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
        </div>
        <div class="space-y-2">
          <Label
            >{{ $t('common.description') }}
            <span class="text-muted-foreground">({{ $t('common.optional') }})</span></Label
          >
          <Textarea
            v-model="form.description"
            :placeholder="$t('roles.form.descriptionPlaceholder')"
            :disabled="isLoading"
            rows="3"
          />
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
          <Button type="submit" :disabled="isLoading || !form.name.trim() || (isEdit && !isDirty)">
            <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
            {{ isEdit ? $t('common.saveChanges') : $t('common.create') }}
          </Button>
        </DialogFooter>
      </form>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { reactive, ref, computed, watch } from 'vue'
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
import { Textarea } from '@/platform/components/ui/textarea'
import { Label } from '@/platform/components/ui/label'
import { useToast } from '@/platform/components/ui/toast/use-toast'
import { useRolesStore } from '@/platform/stores/roles'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import type { RoleOut } from '@/platform/types'

const props = defineProps<{ open: boolean; role?: RoleOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [role: RoleOut | null] }>()

const { t } = useI18n()
const { toast } = useToast()
const rolesStore = useRolesStore()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const rules = useRules()
const isEdit = computed(() => !!props.role)
const { form, errors, validate, clearErrors } = useValidation({
  name: rules.required,
  description: [],
})
const isLoading = ref(false)
const errorMessage = ref('')
const baseline = reactive({ name: '', description: '' })

const isDirty = computed(
  () => form.name !== baseline.name || form.description !== baseline.description,
)

watch(
  [() => props.open, () => props.role],
  ([open]) => {
    if (!open) return
    form.name = props.role?.name ?? ''
    form.description = props.role?.description ?? ''
    baseline.name = form.name
    baseline.description = form.description
    clearErrors()
    errorMessage.value = ''
  },
  { immediate: true },
)

async function onSubmit() {
  if (!validate()) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    const payload = { name: form.name, description: form.description || null }
    if (isEdit.value && props.role) {
      await rolesStore.patch(props.role.id, payload)
      toast({ title: t('roles.form.saved') })
      emit('update:open', false)
      emit('saved', null)
    } else {
      const newRole = await rolesStore.create(payload)
      toast({ title: t('roles.form.created') })
      emit('update:open', false)
      emit('saved', newRole)
    }
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    errorMessage.value = fieldErrors['body__name'] ?? resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
