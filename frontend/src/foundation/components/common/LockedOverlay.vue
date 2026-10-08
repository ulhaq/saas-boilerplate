<template>
  <div class="relative">
    <div
      v-if="locked"
      class="absolute -inset-4 z-10 flex flex-col items-center justify-center gap-3 rounded-lg bg-muted/70 backdrop-blur-xs"
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
import { Button } from '@/foundation/components/ui/button'
import { appConfig } from '@/foundation/config'
import { useEntitlements } from '@/foundation/entitlements'
import type { PlanFeatureValue } from '@/foundation/constants'

const props = defineProps<{ feature: PlanFeatureValue }>()

const { hasFeature } = useEntitlements()
const locked = computed(() => !hasFeature(props.feature))
</script>
