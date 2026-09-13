<template>
  <div class="flex items-center justify-between">
    <p class="text-xs text-muted-foreground">
      {{ $t('common.showing', { from, to, total }) }}
    </p>
    <div class="flex items-center gap-1">
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        class="h-8 w-8 p-0"
        @click="$emit('update:page', 1)"
      >
        <ChevronsLeft class="w-3.5 h-3.5" />
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="page <= 1"
        class="h-8 w-8 p-0"
        @click="$emit('update:page', page - 1)"
      >
        <ChevronLeft class="w-3.5 h-3.5" />
      </Button>
      <span class="text-sm text-muted-foreground px-2 min-w-[80px] text-center">
        {{ page }} / {{ totalPages }}
      </span>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= totalPages"
        class="h-8 w-8 p-0"
        @click="$emit('update:page', page + 1)"
      >
        <ChevronRight class="w-3.5 h-3.5" />
      </Button>
      <Button
        variant="outline"
        size="sm"
        :disabled="page >= totalPages"
        class="h-8 w-8 p-0"
        @click="$emit('update:page', totalPages)"
      >
        <ChevronsRight class="w-3.5 h-3.5" />
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'

useI18n()

const props = defineProps<{
  total: number
  page: number
  pageSize: number
  totalPages: number
}>()

defineEmits<{
  'update:page': [page: number]
  'update:pageSize': [size: number]
}>()

const from = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.pageSize + 1))
const to = computed(() => Math.min(props.page * props.pageSize, props.total))
</script>
