<route lang="yaml">
meta:
  layout: auth
  guestOnly: true
  breadcrumb: auth.registerTitle
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('auth.createAccount') }}</CardTitle>
      <CardDescription>{{ $t('auth.verifyEmailDescription') }}</CardDescription>
    </CardHeader>
    <CardContent>
      <div v-if="sent" class="text-center py-4 space-y-2">
        <div class="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center mx-auto">
          <MailCheck v-if="awaitingVerification" class="w-5 h-5 text-primary" />
          <CheckCircle2 v-else class="w-5 h-5 text-primary" />
        </div>
        <p class="text-sm text-muted-foreground">{{ responseMessage }}</p>
        <p v-if="awaitingVerification" class="text-sm text-muted-foreground">
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
            v-model="form.email"
            type="text"
            :placeholder="$t('auth.emailPlaceholder')"
            :disabled="isLoading"
          />
          <p v-if="errors.email" class="text-xs text-destructive">{{ errors.email }}</p>
        </div>

        <div
          class="space-y-1 rounded-md p-3 transition-colors"
          :class="
            termsError
              ? 'bg-destructive/5 border border-destructive/30'
              : 'border border-transparent'
          "
        >
          <div class="flex items-start space-x-2">
            <Checkbox
              id="terms-accepted"
              :model-value="termsAccepted"
              :disabled="isLoading"
              class="mt-0.5"
              @update:model-value="onTermsChange"
            />
            <Label for="terms-accepted" class="text-sm font-normal leading-snug cursor-pointer">
              <i18n-t keypath="gdpr.consentLabel" tag="span" scope="global">
                <template #terms>
                  <RouterLink
                    :to="localePath('terms')"
                    target="_blank"
                    class="underline hover:text-primary"
                    @click.stop
                  >
                    {{ $t('gdpr.consentTermsLink') }}
                  </RouterLink>
                </template>
                <template #privacy>
                  <RouterLink
                    :to="localePath('privacy')"
                    target="_blank"
                    class="underline hover:text-primary"
                    @click.stop
                  >
                    {{ $t('gdpr.consentPrivacyLink') }}
                  </RouterLink>
                </template>
              </i18n-t>
            </Label>
          </div>
          <p v-if="termsError" class="text-xs text-destructive pl-6">{{ termsError }}</p>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.createAccount') }}
        </Button>
      </form>
    </CardContent>
    <CardFooter v-if="!sent" class="pt-0">
      <p class="text-sm text-muted-foreground text-center w-full">
        {{ $t('auth.alreadyHaveAccount') }}
        <RouterLink to="/login" class="text-foreground font-medium hover:underline">
          {{ $t('auth.signIn') }}
        </RouterLink>
      </p>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Loader2, MailCheck, CheckCircle2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import { Checkbox } from '@/platform/components/ui/checkbox'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { useAuthStore } from '@/platform/stores/auth'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { useI18n } from 'vue-i18n'
import { useLocalePath } from '@/platform/composables/useLocalePath'

const { localePath } = useLocalePath()

const { resolveError, resolveFieldErrors } = useErrorHandler()
const rules = useRules()
const { form, errors, validate } = useValidation({ email: rules.email })
const { t, locale } = useI18n()
const authStore = useAuthStore()

const isLoading = ref(false)
const errorMessage = ref('')
const sent = ref(false)
const responseMessage = ref('')
const awaitingVerification = ref(false)
const termsAccepted = ref(false)
const termsError = ref('')

function onTermsChange(v: boolean | 'indeterminate') {
  termsAccepted.value = v === true
  termsError.value = ''
}

async function onSubmit() {
  if (!validate()) return
  if (!termsAccepted.value) {
    termsError.value = t('gdpr.consentRequired')
    return
  }

  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.register({
      email: form.email,
      terms_accepted: true,
      locale: locale.value,
    })
    responseMessage.value = t('auth.verifyEmailSent')
    awaitingVerification.value = true
    sent.value = true
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    if (fieldErrors['body__email']) {
      errors.email = fieldErrors['body__email']
    } else {
      errorMessage.value = resolveError(err)
    }
  } finally {
    isLoading.value = false
  }
}
</script>
