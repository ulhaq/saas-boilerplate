<template>
  <form class="space-y-4" @submit.prevent="onSubmit">
    <div class="space-y-2">
      <Label for="mfa-code">
        {{ useRecovery ? $t('auth.mfaRecoveryCode') : $t('auth.mfaCode') }}
      </Label>
      <Input
        v-if="useRecovery"
        id="mfa-code"
        v-model="code"
        autocomplete="off"
        placeholder="xxxxx-xxxxx"
        maxlength="11"
        :disabled="isLoading"
        class="font-mono tracking-widest"
        autofocus
      />
      <OtpInput
        v-else
        id="mfa-code"
        v-model="code"
        :disabled="isLoading"
        autofocus
        @complete="onComplete"
      />
      <p class="text-xs text-muted-foreground">
        {{ useRecovery ? $t('auth.mfaRecoveryCodeHint') : $t('auth.mfaCodeHint') }}
      </p>
    </div>

    <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

    <Button
      type="submit"
      class="w-full"
      :disabled="isLoading || (useRecovery ? !code.trim() : code.length !== 6)"
    >
      <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
      {{ $t('auth.mfaVerify') }}
    </Button>

    <div class="flex items-center justify-between text-xs">
      <button
        type="button"
        class="text-muted-foreground hover:text-foreground transition-colors"
        :disabled="isLoading"
        @click="toggleRecovery"
      >
        {{ useRecovery ? $t('auth.mfaUseAuthenticator') : $t('auth.mfaUseRecoveryCode') }}
      </button>
      <button
        type="button"
        class="text-muted-foreground hover:text-foreground transition-colors"
        :disabled="isLoading"
        @click="$emit('cancel')"
      >
        {{ $t('auth.backToSignIn') }}
      </button>
    </div>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2 } from 'lucide-vue-next'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import OtpInput from '@/platform/components/common/OtpInput.vue'

// Second sign-in step: exchanges an MFA challenge token plus a TOTP or
// recovery code for a session.
const props = defineProps<{ mfaToken: string }>()
const emit = defineEmits<{
  (e: 'verified'): void
  (e: 'cancel'): void
}>()

const { t } = useI18n()
const authStore = useAuthStore()
const { resolveError } = useErrorHandler()

const code = ref('')
const useRecovery = ref(false)
const isLoading = ref(false)
const errorMessage = ref('')

function toggleRecovery() {
  useRecovery.value = !useRecovery.value
  code.value = ''
  errorMessage.value = ''
}

// Filling the last box submits right away (also covers paste/autofill).
function onComplete(value: string) {
  code.value = value
  onSubmit()
}

async function onSubmit() {
  if (isLoading.value || !code.value.trim()) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.verifyMfa(props.mfaToken, code.value.trim())
    emit('verified')
  } catch (err: unknown) {
    const e = err as { response?: { data?: { error_code?: string } } }
    // The challenge token lives a few minutes; once it expires only a fresh
    // password sign-in helps.
    if (['signature_expired', 'signature_invalid'].includes(e?.response?.data?.error_code ?? '')) {
      errorMessage.value = t('auth.mfaChallengeExpired')
    } else {
      errorMessage.value = resolveError(err)
    }
    code.value = ''
  } finally {
    isLoading.value = false
  }
}
</script>
