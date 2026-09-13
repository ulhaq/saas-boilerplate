<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{
          isEdit ? $t('organizations.form.editTitle') : $t('organizations.form.createTitle')
        }}</DialogTitle>
        <DialogDescription>
          {{
            isEdit
              ? $t('organizations.form.editDescription')
              : $t('organizations.form.createDescription')
          }}
        </DialogDescription>
      </DialogHeader>

      <form class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label>{{ $t('common.name') }}</Label>
          <Input
            v-model="form.name"
            :placeholder="$t('organizations.form.namePlaceholder')"
            :disabled="isLoading"
          />
          <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
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
import { Label } from '@/platform/components/ui/label'
import { useToast } from '@/platform/components/ui/toast/use-toast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useOrganizationsStore } from '@/platform/stores/organizations'
import { useAuthStore } from '@/platform/stores/auth'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { appConfig } from '@/platform/config'
import type { OrganizationOut } from '@/platform/types'

const props = defineProps<{ open: boolean; organization?: OrganizationOut | null }>()
const emit = defineEmits<{ 'update:open': [boolean]; saved: [] }>()

const { t } = useI18n()
const { toast } = useToast()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const organizationStore = useOrganizationsStore()
const authStore = useAuthStore()
const rules = useRules()
const isEdit = computed(() => !!props.organization)
const { form, errors, validate, clearErrors } = useValidation({ name: rules.required })
const isLoading = ref(false)
const errorMessage = ref('')
const baseline = reactive({ name: '' })

const isDirty = computed(() => form.name !== baseline.name)

watch(
  [() => props.open, () => props.organization],
  ([open]) => {
    if (!open) return
    form.name = props.organization?.name ?? ''
    baseline.name = form.name
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
    if (isEdit.value && props.organization) {
      await organizationStore.patch(props.organization.id, { name: form.name })
      toast({ title: t('organizations.form.saved') })
      await organizationStore.fetchOrganizations()
      emit('update:open', false)
      emit('saved')
      return
    }

    const org = await organizationStore.create({ name: form.name })
    // Switch into the newly created org and hard-navigate home so the app
    // re-bootstraps permissions/subscription for the new tenant (mirrors the
    // org switcher in AppSidebar).
    await authStore.switchOrganization(org.id)
    window.location.assign(appConfig.homeRoute)
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    errorMessage.value = fieldErrors['body__name'] ?? resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
