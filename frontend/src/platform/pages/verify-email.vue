<route lang="yaml">
meta:
  layout: auth
  guestOnly: true
  breadcrumb: auth.verifyEmailTitle
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('auth.verifyEmailTitle') }}</CardTitle>
      <CardDescription v-if="!setupToken && !errorMsg">
        {{ $t('auth.verifyingEmail') }}
      </CardDescription>
      <CardDescription v-else-if="setupToken">
        {{ $t('auth.completeProfileDescription') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <!-- Verifying state -->
      <div v-if="verifying" class="flex justify-center py-6">
        <Loader2 class="w-6 h-6 animate-spin text-muted-foreground" />
      </div>

      <!-- Error state -->
      <div v-else-if="errorMsg" class="text-center py-4 space-y-2">
        <p class="text-sm text-destructive">{{ errorMsg }}</p>
        <RouterLink
          to="/register"
          class="text-sm text-foreground font-medium hover:underline block mt-2"
        >
          {{ $t('auth.registerAgain') }}
        </RouterLink>
      </div>

      <!-- Complete profile form -->
      <form v-else-if="setupToken" class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="name">{{ $t('common.name') }}</Label>
          <Input
            id="name"
            v-model="form.name"
            :placeholder="$t('users.form.namePlaceholder')"
            :disabled="isLoading"
            autofocus
          />
          <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
        </div>
        <div class="space-y-2">
          <Label for="password">{{ $t('common.password') }}</Label>
          <PasswordInput
            id="password"
            v-model="form.password"
            :placeholder="$t('common.minCharacters')"
            :disabled="isLoading"
          />
          <PasswordStrength :password="form.password" />
          <p v-if="errors.password" class="text-xs text-destructive">{{ errors.password }}</p>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.getStarted') }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { resolveError } = useErrorHandler()

const token = (route.query.token as string) || ''
if (token) {
  router.replace({ path: route.path })
}

const verifying = ref(!!token)
const errorMsg = ref('')
const setupToken = ref('')

const { t } = useI18n()
const rules = useRules()
const { form, errors, validate } = useValidation({
  name: rules.required,
  password: rules.password,
})
const isLoading = ref(false)
const errorMessage = ref('')

onMounted(async () => {
  if (!token) {
    errorMsg.value = t('auth.invalidVerifyLink')
    verifying.value = false
    return
  }
  try {
    const data = await authStore.verifyEmail({ token })
    setupToken.value = data.setup_token
  } catch (err: unknown) {
    errorMsg.value = resolveError(err)
  } finally {
    verifying.value = false
  }
})

async function onSubmit() {
  if (!validate()) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.completeRegistration(setupToken.value, form.name, form.password)
    router.push('/settings/billing')
  } catch (err: unknown) {
    errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
