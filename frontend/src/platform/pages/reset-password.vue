<route lang="yaml">
meta:
  layout: auth
  guestOnly: true
  breadcrumb: auth.setNewPassword
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('auth.setNewPassword') }}</CardTitle>
      <CardDescription>{{ $t('auth.setNewPasswordDescription') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="!token" class="text-center py-4">
        <p class="text-sm text-destructive">{{ $t('auth.invalidToken') }}</p>
        <RouterLink
          to="/forgot-password"
          class="text-sm text-foreground font-medium hover:underline block mt-2"
        >
          {{ $t('auth.requestNewLink') }}
        </RouterLink>
      </div>
      <div v-else-if="success" class="text-center py-4 space-y-2">
        <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
          <CheckCircle2 class="w-5 h-5 text-primary" />
        </div>
        <p class="font-medium text-sm">{{ $t('auth.passwordUpdatedSuccess') }}</p>
        <RouterLink
          to="/login"
          class="text-sm text-foreground font-medium hover:underline block mt-4"
        >
          {{ $t('auth.signIn') }}
        </RouterLink>
      </div>
      <form v-else class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="password">{{ $t('auth.newPassword') }}</Label>
          <PasswordInput
            id="password"
            v-model="form.password"
            :placeholder="$t('common.minCharacters')"
            :disabled="isLoading"
          />
          <PasswordStrength :password="form.password" />
          <p v-if="errors.password" class="text-xs text-destructive">{{ errors.password }}</p>
        </div>
        <div class="space-y-2">
          <Label for="confirm">{{ $t('auth.confirmPassword') }}</Label>
          <PasswordInput
            id="confirm"
            v-model="form.confirm"
            :placeholder="$t('auth.repeatPassword')"
            :disabled="isLoading"
          />
          <p v-if="errors.confirm" class="text-xs text-destructive">{{ errors.confirm }}</p>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.updatePassword') }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { Loader2, CheckCircle2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { resolveError } = useErrorHandler()
const token = (route.query.token as string) || ''

if (token) {
  router.replace({ path: route.path })
}

const rules = useRules()
const { form, errors, validate } = useValidation((f) => ({
  password: rules.password,
  confirm: rules.match(() => f.password),
}))
const isLoading = ref(false)
const errorMessage = ref('')
const success = ref(false)

async function onSubmit() {
  if (!validate()) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.resetPassword({ token, password: form.password })
    success.value = true
  } catch (err: unknown) {
    errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
