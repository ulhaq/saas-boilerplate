<template>
  <div class="space-y-4">
    <!-- Toolbar slot -->
    <div v-if="$slots.toolbar" class="flex items-center gap-3">
      <slot name="toolbar" />
    </div>

    <!-- Table -->
    <div class="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow class="bg-muted/40 hover:bg-muted/40">
            <TableHead v-if="selectable" class="w-10">
              <Checkbox
                :model-value="allSelected"
                :aria-label="$t('common.selectAll')"
                @update:model-value="toggleAll"
              />
            </TableHead>
            <TableHead
              v-for="col in columns"
              :key="col.key"
              :class="[
                col.class,
                col.sortable && 'cursor-pointer select-none hover:text-foreground',
              ]"
              @click="col.sortable ? handleSort(col.key) : undefined"
            >
              <div class="flex items-center gap-1">
                {{ col.label }}
                <ArrowUp
                  v-if="col.sortable && sortField === col.key && !sortDesc"
                  class="w-3.5 h-3.5"
                />
                <ArrowDown
                  v-else-if="col.sortable && sortField === col.key && sortDesc"
                  class="w-3.5 h-3.5"
                />
                <ArrowUpDown
                  v-else-if="col.sortable"
                  class="w-3.5 h-3.5 text-muted-foreground/60"
                />
              </div>
            </TableHead>
            <TableHead v-if="$slots.actions" class="w-20 text-right">{{
              $t('common.actions')
            }}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <!-- Loading -->
          <template v-if="loading">
            <TableRow v-for="n in pageSize" :key="`skeleton-${n}`">
              <TableCell v-if="selectable">
                <Skeleton class="h-4 w-4" />
              </TableCell>
              <TableCell v-for="col in columns" :key="col.key">
                <Skeleton class="h-8 w-full max-w-[200px]" />
              </TableCell>
              <TableCell v-if="$slots.actions">
                <Skeleton class="h-8 w-16 ml-auto" />
              </TableCell>
            </TableRow>
          </template>
          <!-- Empty -->
          <template v-else-if="!items.length">
            <TableRow>
              <TableCell
                :colspan="columns.length + (selectable ? 1 : 0) + ($slots.actions ? 1 : 0)"
                class="h-52 p-0"
              >
                <slot v-if="$slots.empty" name="empty" />
                <EmptyState
                  v-else
                  :title="emptyTitle"
                  :description="emptyDescription"
                  :icon="emptyIcon"
                />
              </TableCell>
            </TableRow>
          </template>
          <!-- Data -->
          <template v-else>
            <TableRow
              v-for="item in items"
              :key="(item as Record<string, unknown>)[rowKey] as string"
              class="group transition-colors"
              :class="[
                rowClass?.(item),
                onRowClick ? 'cursor-pointer hover:bg-muted/60' : 'hover:bg-muted/30',
              ]"
              @click="onRowClick?.(item)"
            >
              <TableCell v-if="selectable" class="w-10" @click.stop>
                <Checkbox
                  :model-value="isSelected(item)"
                  :aria-label="$t('common.select')"
                  @update:model-value="toggleRow(item)"
                />
              </TableCell>
              <slot name="row" :item="item" />
              <TableCell v-if="$slots.actions" class="text-right" @click.stop>
                <slot name="actions" :item="item" />
              </TableCell>
            </TableRow>
          </template>
        </TableBody>
      </Table>
    </div>

    <!-- Pagination -->
    <DataTablePagination
      v-if="showPagination"
      :total="total"
      :page="page"
      :page-size="pageSize"
      :total-pages="totalPages"
      @update:page="$emit('update:page', $event)"
      @update:page-size="$emit('update:pageSize', $event)"
    />
  </div>
</template>

<script setup lang="ts" generic="T">
import { ref, computed, type Component } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-vue-next'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/platform/components/ui/table'
import { Skeleton } from '@/platform/components/ui/skeleton'
import { Checkbox } from '@/platform/components/ui/checkbox'
import EmptyState from './EmptyState.vue'
import DataTablePagination from './DataTablePagination.vue'

useI18n()

export interface ColumnDef {
  key: string
  label: string
  sortable?: boolean
  class?: string
}

const props = withDefaults(
  defineProps<{
    columns: ColumnDef[]
    items: T[]
    total: number
    page?: number
    pageSize?: number
    totalPages?: number
    loading?: boolean
    rowKey?: string
    rowClass?: (item: T) => string | undefined
    onRowClick?: (item: T) => void
    emptyTitle?: string
    emptyDescription?: string
    emptyIcon?: Component
    showPagination?: boolean
    selectable?: boolean
    selected?: (string | number)[]
  }>(),
  {
    rowKey: 'id',
    showPagination: true,
    selectable: false,
    selected: () => [],
  },
)

const emit = defineEmits<{
  sort: [field: string, desc: boolean]
  'update:page': [page: number]
  'update:pageSize': [size: number]
  'update:selected': [selected: (string | number)[]]
}>()

function keyOf(item: T): string | number {
  return (item as Record<string, unknown>)[props.rowKey] as string | number
}

function isSelected(item: T): boolean {
  return props.selected.includes(keyOf(item))
}

const allSelected = computed(
  () => props.items.length > 0 && props.items.every((item) => isSelected(item)),
)

function toggleRow(item: T) {
  const key = keyOf(item)
  emit(
    'update:selected',
    isSelected(item) ? props.selected.filter((k) => k !== key) : [...props.selected, key],
  )
}

function toggleAll() {
  if (allSelected.value) {
    const pageKeys = new Set(props.items.map(keyOf))
    emit(
      'update:selected',
      props.selected.filter((k) => !pageKeys.has(k)),
    )
  } else {
    const merged = new Set([...props.selected, ...props.items.map(keyOf)])
    emit('update:selected', [...merged])
  }
}

const sortField = ref<string | null>(null)
const sortDesc = ref(false)

function handleSort(key: string) {
  if (sortField.value === key && sortDesc.value) {
    sortField.value = null
    sortDesc.value = false
    emit('sort', '', false)
  } else if (sortField.value === key) {
    sortDesc.value = true
    emit('sort', key, true)
  } else {
    sortField.value = key
    sortDesc.value = false
    emit('sort', key, false)
  }
}
</script>
