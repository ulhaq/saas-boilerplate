<template>
  <AppBanner v-if="activeCase === 'past_due'" variant="danger">
    {{ $t('subscription.paymentFailed') }}
    <template #cta>
      <Button
        size="sm"
        class="shrink-0 bg-destructive hover:bg-destructive/90 text-destructive-foreground"
        :disabled="isPortalLoading"
        @click="handlePortal"
      >
        <Loader2 v-if="isPortalLoading" class="w-3.5 h-3.5 mr-1.5 animate-spin" />
        <CreditCard v-else class="w-3.5 h-3.5 mr-1.5" />
        {{ $t('subscription.updatePaymentMethod') }}
      </Button>
    </template>
  </AppBanner>

  <AppBanner v-else-if="activeCase === 'trial_ending'" variant="warning">
    {{ $t('subscription.trialEnding', { time: timeRemaining }) }}
    <template #cta="{ textClass }">
      <RouterLink
        to="/settings/billing"
        class="shrink-0 text-sm font-medium underline underline-offset-2 hover:opacity-80"
        :class="textClass"
      >
        {{ $t('subscription.manageBilling') }}
      </RouterLink>
    </template>
  </AppBanner>

  <AppBanner v-else-if="activeCase === 'unused_trial'" variant="success">
    {{ $t('subscription.unusedTrialBanner') }}
    <template #cta>
      <Button
        size="sm"
        class="shrink-0 bg-success hover:bg-success/90 text-success-foreground"
        @click="router.push('/settings/billing')"
      >
        {{ $t('subscription.startFreeTrial') }}
      </Button>
    </template>
  </AppBanner>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { formatDuration, intervalToDuration } from 'date-fns'
import { da as daLocale, enUS as enLocale } from 'date-fns/locale'
import type { Locale } from 'date-fns'
import { Loader2, CreditCard } from 'lucide-vue-next'
import type { SupportedLocale } from '@/plugins/i18n'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { Button } from '@/platform/components/ui/button'
import { MS_PER_DAY } from '@/platform/constants'

const dateFnsLocales: Record<SupportedLocale, Locale> = { da: daLocale, en: enLocale }

const router = useRouter()
const { locale } = useI18n()
const subscriptionStore = useSubscriptionStore()
const { toast } = useToast()
const { resolveError } = useErrorHandler()

const isPortalLoading = ref(false)

onMounted(() => {
  if (subscriptionStore.availableTrialDays === null) subscriptionStore.fetchAvailableTrialDays()
})

type BannerCase = 'past_due' | 'trial_ending' | 'unused_trial' | null

const activeCase = computed((): BannerCase => {
  if (subscriptionStore.subscriptionStatus === 'past_due') return 'past_due'

  if (
    subscriptionStore.subscriptionStatus === 'trialing' &&
    subscriptionStore.subscriptionTrialEnd
  ) {
    const msRemaining = new Date(subscriptionStore.subscriptionTrialEnd).getTime() - Date.now()
    if (msRemaining <= 3 * MS_PER_DAY) return 'trial_ending'
  }

  if (!subscriptionStore.trialUsed && (subscriptionStore.availableTrialDays ?? 0) > 0)
    return 'unused_trial'

  return null
})

const timeRemaining = computed(() => {
  if (!subscriptionStore.subscriptionTrialEnd) return ''
  const end = new Date(subscriptionStore.subscriptionTrialEnd)
  const now = new Date()
  if (end <= now) return ''
  const duration = intervalToDuration({ start: now, end })
  const moreThan24h = end.getTime() - now.getTime() >= MS_PER_DAY
  return formatDuration(duration, {
    format: moreThan24h ? ['days', 'hours'] : ['hours', 'minutes'],
    locale: dateFnsLocales[locale.value as SupportedLocale],
  })
})

async function handlePortal() {
  isPortalLoading.value = true
  try {
    const data = await subscriptionStore.getPortalUrl()
    const parsed = new URL(data.portal_url)
    if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error('Invalid URL protocol')
    window.open(data.portal_url, '_blank', 'noopener,noreferrer')
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    isPortalLoading.value = false
  }
}
</script>
