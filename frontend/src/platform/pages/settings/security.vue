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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Card, CardContent } from '@/platform/components/ui/card'
import { Label } from '@/platform/components/ui/label'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import PasswordStrength from '@/platform/components/common/PasswordStrength.vue'
import { useProfileStore } from '@/platform/stores/profile'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { useFormGuard } from '@/platform/composables/useFormGuard'
import { useSaveFeedback } from '@/platform/composables/useSaveFeedback'

const { t } = useI18n()
const profileStore = useProfileStore()
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
