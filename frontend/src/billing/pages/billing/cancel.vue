<route lang="yaml">
meta:
  layout: dashboard
  requiresAuth: true
  breadcrumb: subscription.checkoutCancelled
</route>

<template>
  <div class="animate-fade-in space-y-6">
    <PageHeader :title="$t('subscription.title')" />

    <div class="rounded-lg border p-6 space-y-4">
      <div>
        <h3 class="font-semibold text-lg">{{ $t('subscription.checkoutCancelled') }}</h3>
        <p class="text-muted-foreground text-sm mt-0.5">
          {{ $t('subscription.checkoutCancelledDescription') }}
        </p>
      </div>
      <Button variant="outline" @click="router.push('/settings/billing')">
        {{ $t('subscription.returnToBilling') }}
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Button } from '@/platform/components/ui/button'
import PageHeader from '@/platform/components/common/PageHeader.vue'

const router = useRouter()
</script>
