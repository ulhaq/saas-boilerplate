<template>
  <ul v-if="rows.length" class="space-y-1.5">
    <li
      v-for="row in rows"
      :key="row.label"
      class="flex items-center gap-1.5 text-xs"
      :class="row[planName] === false ? 'opacity-40' : ''"
    >
      <Check v-if="row[planName] !== false" class="w-3 h-3 shrink-0 text-success" />
      <Minus v-else class="w-3 h-3 shrink-0" />
      <span class="text-muted-foreground inline-flex items-center gap-1">
        <span v-if="typeof row[planName] === 'string'" class="font-medium text-foreground">{{
          row[planName]
        }}</span>
        <template v-if="!row.stat">{{ row.label }}</template>
        <Popover v-if="row.details?.length">
          <PopoverTrigger as-child>
            <button class="text-muted-foreground/50 hover:text-muted-foreground transition-colors">
              <Info class="w-3 h-3" />
            </button>
          </PopoverTrigger>
          <PopoverContent class="w-56 p-3" align="start">
            <p class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
              {{ row.label }}
            </p>
            <ul v-if="row.details?.length" class="space-y-1">
              <li v-for="detail in row.details" :key="detail" class="text-xs text-muted-foreground">
                {{ detail }}
              </li>
            </ul>
          </PopoverContent>
        </Popover>
      </span>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { Check, Info, Minus } from 'lucide-vue-next'
import { Popover, PopoverContent, PopoverTrigger } from '@/platform/components/ui/popover'
import type { ComparisonRow } from '@/platform/composables/useBillingFormat'

defineProps<{ planName: string; rows: ComparisonRow[] }>()
</script>
