<route lang="yaml">
meta:
  layout: auth
  breadcrumb: settings.changeEmail.confirmTitle
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('settings.changeEmail.confirmTitle') }}</CardTitle>
    </CardHeader>
    <CardContent>
      <div v-if="state === 'confirming'" class="flex justify-center py-6">
        <Loader2 class="w-6 h-6 animate-spin text-muted-foreground" />
      </div>

      <div v-else-if="state === 'done'" class="text-center py-4 space-y-4">
        <CheckCircle2 class="w-8 h-8 mx-auto text-primary" />
        <p class="text-sm text-muted-foreground">{{ $t('settings.changeEmail.confirmed') }}</p>
        <Button class="w-full" @click="router.push('/login')">
          {{ $t('auth.signIn') }}
        </Button>
      </div>

      <div v-else class="text-center py-4 space-y-2">
        <p class="text-sm text-destructive">{{ errorMsg }}</p>
        <p class="text-sm text-muted-foreground">{{ $t('settings.changeEmail.requestAgain') }}</p>
      </div>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CheckCircle2, Loader2 } from 'lucide-vue-next'
import { Card, CardContent, CardHeader, CardTitle } from '@/platform/components/ui/card'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'

// Target of the link emailed to the new address. Not guest-only: the link
// may be opened while signed in (that session is ended on success).
const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const { resolveError } = useErrorHandler()

const token = (route.query.token as string) || ''
const state = ref<'confirming' | 'done' | 'error'>(token ? 'confirming' : 'error')
const errorMsg = ref(token ? '' : t('settings.changeEmail.invalidLink'))

onMounted(async () => {
  if (!token) return
  // Keep the token out of history once read.
  window.history.replaceState(null, '', route.path)
  try {
    await authStore.confirmEmailChange(token)
    state.value = 'done'
  } catch (err: unknown) {
    const code = (err as { response?: { data?: { error_code?: string } } })?.response?.data
      ?.error_code
    errorMsg.value = ['signature_invalid', 'signature_expired', 'token_invalid'].includes(
      code ?? '',
    )
      ? t('settings.changeEmail.invalidLink')
      : resolveError(err)
    state.value = 'error'
  }
})
</script>
