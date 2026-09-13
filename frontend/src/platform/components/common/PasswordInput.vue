<template>
  <div class="relative">
    <input
      v-model="modelValue"
      v-bind="$attrs"
      :type="show ? 'text' : 'password'"
      :class="
        cn(
          'flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 pr-9 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50',
          props.class,
        )
      "
    />
    <!--
      Icon-only toggle: the eye conveys the state visually but contributes no
      text, so the button needs an explicit name that flips with `show`.
    -->
    <button
      type="button"
      tabindex="-1"
      class="absolute right-0 top-0 h-9 w-9 flex items-center justify-center text-muted-foreground hover:text-foreground"
      :aria-label="show ? $t('common.hidePassword') : $t('common.showPassword')"
      :aria-pressed="show"
      @click="show = !show"
    >
      <Eye v-if="!show" class="h-4 w-4" aria-hidden="true" />
      <EyeOff v-else class="h-4 w-4" aria-hidden="true" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { HTMLAttributes } from 'vue'
import { useVModel } from '@vueuse/core'
import { Eye, EyeOff } from 'lucide-vue-next'
import { cn } from '@/platform/lib/utils'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  modelValue?: string
  class?: HTMLAttributes['class']
}>()

const emits = defineEmits<{
  (e: 'update:modelValue', payload: string): void
}>()

const modelValue = useVModel(props, 'modelValue', emits, {
  passive: true,
  defaultValue: '',
})

const show = ref(false)
</script>
