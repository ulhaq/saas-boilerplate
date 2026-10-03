<template>
  <div class="flex flex-col items-center justify-center py-12 text-center">
    <div class="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-4">
      <component :is="icon" class="w-6 h-6 text-muted-foreground" />
    </div>
    <p class="text-sm font-medium text-foreground">{{ displayTitle }}</p>
    <p class="text-xs text-muted-foreground mt-1 max-w-xs">{{ displayDescription }}</p>
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { InboxIcon } from 'lucide-vue-next'

const { t } = useI18n()

const props = withDefaults(
  defineProps<{
    title?: string
    description?: string
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon?: any
  }>(),
  {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    icon: () => InboxIcon as any,
  },
)

const displayTitle = computed(() => props.title ?? t('common.noResults'))
const displayDescription = computed(() => props.description ?? t('common.nothingToDisplay'))
</script>
