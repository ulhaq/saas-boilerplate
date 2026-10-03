<template>
  <div class="relative">
    <div
      v-if="locked"
      class="absolute -inset-4 z-10 flex flex-col items-center justify-center gap-3 rounded-lg bg-muted/70 backdrop-blur-sm"
    >
      <p class="text-sm font-medium">{{ $t('planFeature.unavailableMessage') }}</p>
      <Button v-if="appConfig.upgradeRoute" size="sm" as-child>
        <RouterLink :to="appConfig.upgradeRoute">{{ $t('planFeature.upgradeCta') }}</RouterLink>
      </Button>
    </div>
    <div :inert="locked || undefined">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from '@/platform/components/ui/button'
import { appConfig } from '@/platform/config'
import { useEntitlements } from '@/platform/entitlements'
import type { PlanFeatureValue } from '@/platform/constants'

const props = defineProps<{ feature: PlanFeatureValue }>()

const { hasFeature } = useEntitlements()
const locked = computed(() => !hasFeature(props.feature))
</script>
