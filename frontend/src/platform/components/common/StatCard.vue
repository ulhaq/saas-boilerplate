<template>
  <component :is="to ? RouterLink : 'div'" :to="to" :class="to ? 'group block h-full' : 'h-full'">
    <Card
      :class="[
        'relative h-full overflow-hidden transition-all duration-300',
        to && 'cursor-pointer hover:-translate-y-1 hover:shadow-lg hover:border-foreground/15',
      ]"
    >
      <!-- soft accent glow in the corner, tinted by the icon colour -->
      <div
        class="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full opacity-50 blur-2xl transition-opacity duration-300"
        :class="[iconBg, to && 'group-hover:opacity-80']"
        aria-hidden="true"
      />

      <CardContent class="relative pt-6">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-sm font-medium text-muted-foreground">{{ label }}</p>
            <p
              class="mt-2 text-[2rem] leading-none font-bold text-foreground tabular-nums tracking-tight"
            >
              <Skeleton v-if="loading" class="h-8 w-16" />
              <span v-else>{{ value }}</span>
            </p>
            <p
              v-if="hint && !loading"
              class="mt-2 truncate text-xs font-medium text-muted-foreground/80"
            >
              {{ hint }}
            </p>
          </div>
          <div
            class="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 shadow-sm ring-1 ring-inset ring-foreground/5 transition-transform duration-300"
            :class="[iconBg, to && 'group-hover:scale-110']"
          >
            <component :is="icon" class="w-5 h-5" :class="iconColor" />
          </div>
        </div>
      </CardContent>
    </Card>
  </component>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { Card, CardContent } from '@/platform/components/ui/card'
import { Skeleton } from '@/platform/components/ui/skeleton'

defineProps<{
  label: string
  value: string | number
  hint?: string
  icon: unknown
  loading?: boolean
  iconBg?: string
  iconColor?: string
  to?: string
}>()
</script>
