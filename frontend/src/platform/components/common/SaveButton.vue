<template>
  <div class="flex items-center justify-end gap-3">
    <Transition
      enter-active-class="transition-opacity duration-200"
      leave-active-class="transition-opacity duration-300"
      enter-from-class="opacity-0"
      leave-to-class="opacity-0"
    >
      <span
        v-if="saved"
        class="flex items-center gap-1 text-sm font-medium text-success"
        role="status"
        aria-live="polite"
      >
        <Check :stroke-width="3" class="h-4 w-4" />
        {{ savedLabel ?? t('common.saved') }}
      </span>
    </Transition>
    <Button
      :type="type"
      :size="size"
      :variant="variant"
      :class="props.class"
      :disabled="disabled || saving"
    >
      <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
      <slot />
    </Button>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { Loader2, Check } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { Button } from '@/platform/components/ui/button'
import type { ButtonVariants } from '@/platform/components/ui/button'

const props = withDefaults(
  defineProps<{
    saving?: boolean
    saved?: boolean
    disabled?: boolean
    type?: 'submit' | 'button'
    size?: ButtonVariants['size']
    variant?: ButtonVariants['variant']
    class?: HTMLAttributes['class']
    /** Confirmation label shown beside the button on success. Defaults to "Saved". */
    savedLabel?: string
  }>(),
  {
    type: 'submit',
    size: 'sm',
  },
)

const { t } = useI18n()
</script>
