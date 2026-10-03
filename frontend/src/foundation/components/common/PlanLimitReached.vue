<template>
  <div class="flex flex-col items-center gap-3 text-center py-6">
    <div class="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
      <Lock class="w-5 h-5 text-destructive" />
    </div>
    <div>
      <p class="text-sm font-medium">{{ title }}</p>
      <p class="text-xs text-muted-foreground mt-1 max-w-xs">{{ description }}</p>
    </div>
    <div class="flex items-center gap-2">
      <Button size="sm" variant="outline" @click="$emit('dismiss')">
        {{ $t('common.maybeLater') }}
      </Button>
      <Button v-if="appConfig.upgradeRoute" size="sm" as-child>
        <RouterLink :to="appConfig.upgradeRoute">{{ $t('common.upgradePlan') }}</RouterLink>
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Lock } from 'lucide-vue-next'
import { Button } from '@/foundation/components/ui/button'
import { appConfig } from '@/foundation/config'

defineProps<{
  title: string
  description: string
}>()

defineEmits<{ dismiss: [] }>()
</script>
