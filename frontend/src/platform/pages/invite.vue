<route lang="yaml">
meta:
  layout: auth
  breadcrumb: auth.invite.title
</route>

<template>
  <Card>
    <CardHeader class="pb-4">
      <CardTitle as="h2" class="text-lg">{{ $t('auth.invite.title') }}</CardTitle>
      <CardDescription v-if="state === 'new-user'">
        {{ $t('auth.invite.description') }}
      </CardDescription>
    </CardHeader>
    <CardContent>
      <!-- Invalid / expired token -->
      <div v-if="state === 'invalid'" class="text-center py-4 space-y-2">
        <p class="text-sm text-destructive">{{ invalidMessage }}</p>
        <p class="text-sm text-muted-foreground">{{ $t('auth.invite.contactAdmin') }}</p>
      </div>

      <!-- Loading preflight -->
      <div v-else-if="state === 'loading'" class="py-4 space-y-3">
        <Skeleton class="h-10 w-full" />
        <Skeleton class="h-10 w-full" />
        <Skeleton class="h-10 w-full" />
      </div>

      <!-- Logged in as wrong account -->
      <div v-else-if="state === 'wrong-account'" class="text-center py-4 space-y-3">
        <p class="text-sm text-muted-foreground">
          {{ $t('auth.invite.wrongAccount', { email: currentUserEmail }) }}
        </p>
        <p class="text-sm text-muted-foreground">{{ $t('auth.invite.logoutFirst') }}</p>
        <Button class="w-full" :disabled="isLoading" @click="onLogout">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.invite.logout') }}
        </Button>
      </div>

      <!-- Existing user - accept with one click -->
      <div v-else-if="state === 'existing-user'" class="space-y-4">
        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>
        <Button class="w-full" :disabled="isLoading" @click="onAcceptExisting">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.invite.acceptAs', { email: inviteEmail }) }}
        </Button>
      </div>

      <!-- New user - name + password form -->
      <form v-else-if="state === 'new-user'" class="space-y-4" @submit.prevent="onSubmitNew">
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
              id="invite-terms"
              :model-value="termsAccepted"
              :disabled="isLoading"
              class="mt-0.5"
              @update:model-value="onTermsChange"
            />
            <Label for="invite-terms" class="text-sm font-normal leading-snug">
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
          <p v-if="termsError" class="text-xs text-destructive">{{ termsError }}</p>
        </div>

        <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>

        <Button type="submit" class="w-full" :disabled="isLoading">
          <Loader2 v-if="isLoading" class="w-4 h-4 mr-2 animate-spin" />
          {{ $t('auth.invite.accept') }}
        </Button>
      </form>
    </CardContent>
  </Card>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loader2 } from 'lucide-vue-next'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/platform/components/ui/card'
import { Checkbox } from '@/platform/components/ui/checkbox'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import { Button } from '@/platform/components/ui/button'
import { Skeleton } from '@/platform/components/ui/skeleton'
import { appConfig } from '@/platform/config'
import { useAuthStore } from '@/platform/stores/auth'
import { useProfileStore } from '@/platform/stores/profile'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useI18n } from 'vue-i18n'
import { useLocalePath } from '@/platform/composables/useLocalePath'

const { localePath } = useLocalePath()

type InviteState = 'loading' | 'invalid' | 'wrong-account' | 'existing-user' | 'new-user'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const profileStore = useProfileStore()
const { resolveError } = useErrorHandler()

const inviteToken = (route.query.token as string) || ''

const { t } = useI18n()
const state = ref<InviteState>(inviteToken ? 'loading' : 'invalid')
const invalidMessage = ref(inviteToken ? '' : t('auth.invite.invalidLink'))
const inviteEmail = ref('')
const rules = useRules()
const { form, errors, validate } = useValidation({
  name: rules.required,
  password: rules.password,
})
const termsAccepted = ref(false)
const termsError = ref('')
const isLoading = ref(false)
const errorMessage = ref('')

const currentUserEmail = computed(() => profileStore.user?.email ?? '')

onMounted(async () => {
  if (!inviteToken) return

  // Remove the token from the URL without triggering a Vue Router navigation.
  window.history.replaceState(null, '', route.path)

  try {
    const data = await authStore.inviteStatus(inviteToken)
    inviteEmail.value = data.email

    if (authStore.isAuthenticated && currentUserEmail.value !== data.email) {
      state.value = 'wrong-account'
      return
    }

    if (!data.user_exists) {
      state.value = 'new-user'
      return
    }

    state.value = 'existing-user'
  } catch (err: unknown) {
    invalidMessage.value = resolveError(err)
    state.value = 'invalid'
  }
})

async function _finishAccept(
  inviteTokenValue: string,
  name?: string,
  password?: string,
  termsAcceptedVal?: boolean,
) {
  isLoading.value = true
  errorMessage.value = ''
  try {
    await authStore.completeInvite({
      invite_token: inviteTokenValue,
      ...(name !== undefined && { name }),
      ...(password !== undefined && { password }),
      ...(termsAcceptedVal !== undefined && { terms_accepted: termsAcceptedVal }),
    })
    router.push(appConfig.homeRoute)
  } catch (err: unknown) {
    errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}

async function onAcceptExisting() {
  await _finishAccept(inviteToken)
}

function onTermsChange(v: boolean | 'indeterminate') {
  termsAccepted.value = v === true
  termsError.value = ''
}

async function onSubmitNew() {
  if (!validate()) return
  if (!termsAccepted.value) {
    termsError.value = t('gdpr.consentRequired')
    return
  }
  await _finishAccept(inviteToken, form.name, form.password, termsAccepted.value)
}

async function onLogout() {
  isLoading.value = true
  try {
    await authStore.logout()
    // Full reload so onMounted re-runs with the token after the component remounts.
    window.location.href = `${route.path}?token=${encodeURIComponent(inviteToken)}`
  } finally {
    isLoading.value = false
  }
}
</script>
