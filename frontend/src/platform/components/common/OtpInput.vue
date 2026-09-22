<template>
  <PinInputRoot
    :id="id"
    v-model="digits"
    type="number"
    otp
    placeholder="○"
    :disabled="disabled"
    class="flex items-center gap-2"
    @complete="(value: number[]) => emit('complete', value.join(''))"
  >
    <PinInputInput
      v-for="(_, index) in length"
      :key="index"
      :index="index"
      :autofocus="autofocus && index === 0"
      class="h-11 w-10 rounded-md border border-input bg-transparent text-center font-mono text-lg shadow-sm transition-colors placeholder:text-muted-foreground/40 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
    />
  </PinInputRoot>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { PinInputInput, PinInputRoot } from 'reka-ui'

// One box per digit for one-time codes (TOTP). Handles typing, backspace,
// arrow keys and pasting a full code; v-model is the plain digit string.
const props = withDefaults(
  defineProps<{
    modelValue: string
    length?: number
    id?: string
    disabled?: boolean
    autofocus?: boolean
  }>(),
  { length: 6, id: undefined, disabled: false, autofocus: false },
)
const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
  (e: 'complete', value: string): void
}>()

const digits = computed<number[]>({
  get: () => props.modelValue.split('').map(Number),
  set: (value) => emit('update:modelValue', value.join('')),
})
</script>
