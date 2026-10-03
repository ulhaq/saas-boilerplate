<route lang="yaml">
meta:
  breadcrumb: settings.security
</route>

<template>
  <div class="max-w-2xl">
    <PageHeader
      :title="$t('settings.changePassword')"
      :description="$t('settings.changePasswordDescription')"
    />

    <Card>
      <CardContent class="pt-6">
        <form class="space-y-4" @submit.prevent="savePassword">
          <div class="space-y-2">
            <Label>{{ $t('settings.currentPassword') }}</Label>
            <PasswordInput v-model="pwd.current" :disabled="savingPwd" />
            <p v-if="pwdErrors.current" class="text-xs text-destructive">{{ pwdErrors.current }}</p>
          </div>
          <div class="space-y-2">
            <Label>{{ $t('settings.newPassword') }}</Label>
            <PasswordInput
              v-model="pwd.new"
              :placeholder="$t('common.minCharacters')"
              :disabled="savingPwd"
            />
            <PasswordStrength :password="pwd.new" />
            <p v-if="pwdErrors.new" class="text-xs text-destructive">{{ pwdErrors.new }}</p>
          </div>
          <div class="space-y-2">
            <Label>{{ $t('settings.confirmNewPassword') }}</Label>
            <PasswordInput v-model="pwd.confirm" :disabled="savingPwd" />
            <p v-if="pwdErrors.confirm" class="text-xs text-destructive">{{ pwdErrors.confirm }}</p>
          </div>
          <p v-if="pwdError" class="text-sm text-destructive">{{ pwdError }}</p>
          <SaveButton
            :saving="savingPwd"
            :saved="pwdSaved"
            :disabled="!pwd.current || !pwd.new || !pwd.confirm"
          >
            {{ $t('auth.updatePassword') }}
          </SaveButton>
        </form>
      </CardContent>
    </Card>

    <div v-if="mfaEnabled" class="mt-8">
      <MfaSettings />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent } from '@/foundation/components/ui/card'
import { Label } from '@/foundation/components/ui/label'
import PageHeader from '@/foundation/components/common/PageHeader.vue'
import PasswordStrength from '@/foundation/components/common/PasswordStrength.vue'
import MfaSettings from '@/foundation/components/settings/MfaSettings.vue'
import { MFA_ENABLED } from '@/foundation/constants'
import { useProfileStore } from '@/foundation/stores/profile'
import { useErrorHandler } from '@/foundation/composables/useErrorHandler'
import { useValidation } from '@/foundation/composables/useValidation'
import { useRules } from '@/foundation/composables/useRules'
import { useFormGuard } from '@/foundation/composables/useFormGuard'
import { useSaveFeedback } from '@/foundation/composables/useSaveFeedback'

const { t } = useI18n()
const profileStore = useProfileStore()
const mfaEnabled = MFA_ENABLED
const { resolveError } = useErrorHandler()

const rules = useRules()
const {
  form: pwd,
  errors: pwdErrors,
  validate: validatePwd,
} = useValidation((f) => ({
  current: rules.required,
  new: rules.password,
  confirm: rules.match(() => f.new),
}))
const pwdError = ref('')
const { saving: savingPwd, saved: pwdSaved, save: saveWithFeedback } = useSaveFeedback()

useFormGuard(() => !!(pwd.current || pwd.new || pwd.confirm))

async function savePassword() {
  if (!validatePwd()) return

  pwdError.value = ''
  try {
    await saveWithFeedback(() =>
      profileStore.changePassword({
        password: pwd.current,
        new_password: pwd.new,
        confirm_password: pwd.confirm,
      }),
    )
    pwd.current = ''
    pwd.new = ''
    pwd.confirm = ''
    pwdErrors.current = ''
    pwdErrors.new = ''
    pwdErrors.confirm = ''
  } catch (err: unknown) {
    const e = err as { response?: { data?: { error_code?: string } } }
    if (e?.response?.data?.error_code === 'login_failed') {
      pwdErrors.current = t('settings.incorrectCurrentPassword')
    } else {
      pwdError.value = resolveError(err)
    }
  }
}
</script>
