<route lang="yaml">
meta:
  layout: auth
  guestOnly: true
  breadcrumb: auth.loginTitle
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">
        {{ mfaToken ? $t('auth.mfaTitle') : $t('auth.signIn') }}
      </CardTitle>
      <CardDescription>
        {{ mfaToken ? $t('auth.mfaDescription') : $t('auth.signInDescription') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <MfaChallengeForm
        v-if="mfaToken"
        :mfa-token="mfaToken"
        @verified="redirectAfterLogin"
        @cancel="onCancelMfa"
      />
      <form v-else class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="email">{{ $t('common.email') }}</Label>
          <Input
            id="email"
            v-model="email"
            type="text"
            :placeholder="$t('auth.emailPlaceholder')"
            autocomplete="email"
            :disabled="isLoading"
          />
        </div>
        <div class="space-y-2">
          <div class="flex items-center justify-between">
            <Label for="password">{{ $t('common.password') }}</Label>
            <RouterLink
              to="/forgot-password"
              class="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              {{ $t('auth.forgotPassword') }}
            </RouterLink>
          </div>
          <PasswordInput
            id="password"
            v-model="password"
            placeholder="••••••••"
            autocomplete="current-password"
            :disabled="isLoading"
          />
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading || !email.trim() || !password">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.signIn') }}
        </Button>
      </form>
    </CardContent>
    <CardFooter v-if="!mfaToken" class="pt-0">
      <p class="text-sm text-muted-foreground text-center w-full">
        {{ $t('auth.dontHaveAccount') }}
        <RouterLink to="/register" class="text-foreground font-medium hover:underline">
          {{ $t('auth.createOne') }}
        </RouterLink>
      </p>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { appConfig } from '@/platform/config'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import MfaChallengeForm from '@/platform/components/auth/MfaChallengeForm.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const { resolveError } = useErrorHandler()

const email = ref('')
const password = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
// Set when the password was accepted but the account requires a 2FA code.
const mfaToken = ref('')

function redirectAfterLogin() {
  const raw = (route.query.redirect as string) || appConfig.homeRoute
  const redirect = raw.startsWith('/') && !raw.startsWith('//') ? raw : appConfig.homeRoute
  router.push(redirect)
}

function onCancelMfa() {
  mfaToken.value = ''
  password.value = ''
}

async function onSubmit() {
  if (!email.value || !password.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    const challenge = await authStore.login(email.value, password.value)
    if (challenge) {
      mfaToken.value = challenge.mfa_token
      return
    }
    redirectAfterLogin()
  } catch (err: unknown) {
    errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
