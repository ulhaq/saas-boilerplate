<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  breadcrumb: subscription.checkoutSuccess
</route>

<template>
  <div class="animate-fade-in space-y-6">
    <PageHeader :title="$t('subscription.title')" />

    <div v-if="isLoading" class="space-y-4">
      <Skeleton class="h-48 w-full rounded-lg" />
    </div>

    <div v-else-if="isSuccess" class="rounded-lg border p-6 space-y-4">
      <div>
        <h3 class="font-semibold text-lg">{{ $t('subscription.checkoutSuccess') }}</h3>
        <p class="text-muted-foreground text-sm mt-0.5">
          {{ $t('subscription.checkoutSuccessDescription') }}
        </p>
      </div>
      <Button @click="router.push(appConfig.homeRoute)">{{
        $t('subscription.goToDashboard')
      }}</Button>
    </div>

    <div v-else-if="isPending" class="rounded-lg border p-6 space-y-4">
      <div>
        <h3 class="font-semibold text-lg">{{ $t('subscription.checkoutPending') }}</h3>
        <p class="text-muted-foreground text-sm mt-0.5">
          {{ $t('subscription.checkoutPendingDescription') }}
        </p>
      </div>
      <Button variant="outline" @click="router.push('/settings/billing')">
        {{ $t('subscription.returnToBilling') }}
      </Button>
    </div>

    <div v-else class="rounded-lg border p-6 space-y-4">
      <div>
        <h3 class="font-semibold text-lg">{{ $t('subscription.fetchFailed') }}</h3>
        <p class="text-muted-foreground text-sm mt-0.5">{{ fetchError }}</p>
      </div>
      <Button variant="outline" @click="router.push('/settings/billing')">
        {{ $t('subscription.returnToBilling') }}
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { appConfig } from '@/platform/config'
import { useRouter } from 'vue-router'
import { Button } from '@/platform/components/ui/button'
import { Skeleton } from '@/platform/components/ui/skeleton'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'

// The subscription is activated by Stripe webhooks, which can lag the
// redirect back from checkout - poll briefly before settling on "pending".
const POLL_ATTEMPTS = 5
const POLL_INTERVAL_MS = 2000

const router = useRouter()
const subscriptionStore = useSubscriptionStore()
const { resolveError } = useErrorHandler()

const isLoading = ref(true)
const isSuccess = ref(false)
const isPending = ref(false)
const fetchError = ref('')

let stopped = false
onUnmounted(() => {
  stopped = true
})

onMounted(async () => {
  for (let attempt = 1; attempt <= POLL_ATTEMPTS && !stopped; attempt++) {
    try {
      const data = await subscriptionStore.getCurrentSubscription()
      if (data.status === 'active' || data.status === 'trialing') {
        isSuccess.value = true
        isPending.value = false
        isLoading.value = false
        // Sync the global store so the banner and router guard see the
        // activated subscription without a reload.
        await subscriptionStore.fetchSubscriptionStatus()
        return
      }
      isPending.value = true
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        isPending.value = true
      } else {
        fetchError.value = resolveError(err)
        isLoading.value = false
        return
      }
    }
    isLoading.value = false
    if (attempt < POLL_ATTEMPTS) {
      await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS))
    }
  }
})
</script>
