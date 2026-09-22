<template>
  <Dialog :open="open" @update:open="$emit('update:open', $event)">
    <DialogContent class="sm:max-w-md">
      <DialogHeader>
        <DialogTitle>{{ $t('settings.changeEmail.title') }}</DialogTitle>
        <DialogDescription>{{ $t('settings.changeEmail.description') }}</DialogDescription>
      </DialogHeader>

      <form class="space-y-4 mt-2" @submit.prevent="submit">
        <div class="space-y-2">
          <Label for="change-email-new">{{ $t('settings.changeEmail.newEmail') }}</Label>
          <Input
            id="change-email-new"
            v-model="form.newEmail"
            type="email"
            autocomplete="email"
            :disabled="busy"
            autofocus
          />
          <p v-if="errors.newEmail" class="text-xs text-destructive">{{ errors.newEmail }}</p>
        </div>

        <div class="space-y-2">
          <Label for="change-email-password">{{ $t('settings.currentPassword') }}</Label>
          <PasswordInput
            id="change-email-password"
            v-model="form.password"
            autocomplete="current-password"
            :disabled="busy"
          />
          <p v-if="errors.password" class="text-xs text-destructive">{{ errors.password }}</p>
        </div>

        <div v-if="needsCode" class="space-y-2">
          <Label for="change-email-code">
            {{ useRecovery ? $t('auth.mfaRecoveryCode') : $t('auth.mfaCode') }}
          </Label>
          <Input
            v-if="useRecovery"
            id="change-email-code"
            v-model="form.code"
            autocomplete="off"
            placeholder="xxxxx-xxxxx"
            maxlength="11"
            class="font-mono tracking-widest"
            :disabled="busy"
          />
          <OtpInput v-else id="change-email-code" v-model="form.code" :disabled="busy" />
          <p v-if="errors.code" class="text-xs text-destructive">{{ errors.code }}</p>
          <button
            type="button"
            class="text-xs text-muted-foreground hover:text-foreground transition-colors"
            :disabled="busy"
            @click="toggleRecovery"
          >
            {{ useRecovery ? $t('auth.mfaUseAuthenticator') : $t('auth.mfaUseRecoveryCode') }}
          </button>
        </div>

        <p v-if="formError" class="text-sm text-destructive">{{ formError }}</p>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            :disabled="busy"
            @click="$emit('update:open', false)"
          >
            {{ $t('common.cancel') }}
          </Button>
          <Button type="submit" :disabled="!canSubmit">
            <Loader2 v-if="busy" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('settings.changeEmail.submit') }}
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
import PasswordInput from '@/platform/components/common/PasswordInput.vue'
import OtpInput from '@/platform/components/common/OtpInput.vue'
import { useProfileStore } from '@/platform/stores/profile'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { MFA_ENABLED } from '@/platform/constants'

// Starts an email change: re-authenticates (password + 2FA code when on) and
// has the API email a confirmation link to the new address.
const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const { t } = useI18n()
const { toast } = useToast()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const profileStore = useProfileStore()

const form = reactive({ newEmail: '', password: '', code: '' })
const errors = reactive({ newEmail: '', password: '', code: '' })
const formError = ref('')
const busy = ref(false)
const useRecovery = ref(false)
// Also flipped on if the API says a code is required (flags out of sync).
const serverWantsCode = ref(false)

const needsCode = computed(
  () => serverWantsCode.value || (MFA_ENABLED && !!profileStore.user?.mfa_enabled),
)

const canSubmit = computed(() => {
  if (busy.value || !form.newEmail.trim() || !form.password) return false
  if (!needsCode.value) return true
  return useRecovery.value ? !!form.code.trim() : form.code.length === 6
})

watch(
  () => props.open,
  (open) => {
    if (!open) return
    form.newEmail = ''
    form.password = ''
    form.code = ''
    useRecovery.value = false
    serverWantsCode.value = false
    clearErrors()
  },
)

function clearErrors() {
  errors.newEmail = ''
  errors.password = ''
  errors.code = ''
  formError.value = ''
}

function toggleRecovery() {
  useRecovery.value = !useRecovery.value
  form.code = ''
  errors.code = ''
}

async function submit() {
  if (!canSubmit.value) return
  busy.value = true
  clearErrors()
  const newEmail = form.newEmail.trim()
  try {
    await profileStore.requestEmailChange({
      new_email: newEmail,
      password: form.password,
      ...(needsCode.value && { code: form.code.trim() }),
    })
    emit('update:open', false)
    toast({
      title: t('settings.changeEmail.sentTitle'),
      description: t('settings.changeEmail.sentDescription', { email: newEmail }),
    })
  } catch (err: unknown) {
    const code = (err as { response?: { data?: { error_code?: string } } })?.response?.data
      ?.error_code
    const message = resolveError(err)
    if (code === 'login_failed') {
      errors.password = t('settings.incorrectCurrentPassword')
    } else if (code === 'mfa_code_required') {
      serverWantsCode.value = true
      errors.code = message
    } else if (code === 'mfa_code_invalid') {
      errors.code = message
      form.code = ''
    } else if (code === 'email_already_exists' || code === 'email_unchanged') {
      errors.newEmail = message
    } else {
      errors.newEmail = resolveFieldErrors(err)['body__new_email'] ?? ''
      if (!errors.newEmail) formError.value = message
    }
  } finally {
    busy.value = false
  }
}
</script>
