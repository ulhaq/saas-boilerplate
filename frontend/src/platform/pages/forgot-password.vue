<route lang="yaml">
meta:
  layout: auth
  guestOnly: true
  breadcrumb: auth.resetPassword
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('auth.resetPassword') }}</CardTitle>
      <CardDescription>
        {{ $t('auth.resetPasswordDescription') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="sent" class="text-center py-4 space-y-2">
        <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
          <MailCheck class="w-5 h-5 text-primary" />
        </div>
        <p class="font-medium text-sm">{{ $t('auth.checkInbox') }}</p>
        <p class="text-sm text-muted-foreground">
          {{ $t('auth.resetLinkSent') }}
        </p>
        <p class="text-sm text-muted-foreground">
          {{ $t('common.checkSpam') }}
        </p>
        <RouterLink
          to="/login"
          class="text-sm text-foreground font-medium hover:underline block mt-4"
        >
          {{ $t('auth.backToSignIn') }}
        </RouterLink>
      </div>
      <form v-else class="space-y-4" @submit.prevent="onSubmit">
        <div class="space-y-2">
          <Label for="email">{{ $t('common.email') }}</Label>
          <Input
            id="email"
            v-model="email"
            type="text"
            :placeholder="$t('auth.emailPlaceholder')"
            :disabled="isLoading"
          />
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading || !email.trim()">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.sendResetLink') }}
        </Button>

        <RouterLink
          to="/login"
          class="block text-center text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          {{ $t('auth.backToSignIn') }}
        </RouterLink>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, MailCheck } from 'lucide-vue-next'
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

useI18n()
const { resolveError } = useErrorHandler()
const authStore = useAuthStore()

const email = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const sent = ref(false)

async function onSubmit() {
  if (!email.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.requestPasswordReset({ email: email.value })
    sent.value = true
  } catch (err: unknown) {
    errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
