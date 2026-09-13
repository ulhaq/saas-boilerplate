<template>
  <div class="flex flex-col gap-3 mb-6 sm:flex-row sm:items-start sm:justify-between">
    <div>
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-semibold text-foreground">{{ title }}</h1>
        <slot name="title-suffix" />
      </div>
      <p v-if="description" class="text-sm text-muted-foreground mt-0.5">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="flex items-center gap-2 shrink-0 sm:ml-4">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>
