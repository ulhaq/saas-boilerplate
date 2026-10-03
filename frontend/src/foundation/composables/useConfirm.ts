import { reactive } from 'vue'
import { i18n } from '@/plugins/i18n'

type ConfirmVariant = 'destructive' | 'default'

interface ConfirmState {
  open: boolean
  title: string
  description: string
  confirmLabel: string
  variant: ConfirmVariant
  resolve: ((confirmed: boolean) => void) | null
}

const state = reactive<ConfirmState>({
  open: false,
  title: '',
  description: '',
  confirmLabel: '',
  variant: 'destructive',
  resolve: null,
})

export function useConfirm() {
  function confirm(
    title: string,
    description = '',
    confirmLabel = i18n.global.t('common.confirm'),
    variant: ConfirmVariant = 'destructive',
  ): Promise<boolean> {
    return new Promise<boolean>((resolve) => {
      state.open = true
      state.title = title
      state.description = description
      state.confirmLabel = confirmLabel
      state.variant = variant
      state.resolve = resolve
    })
  }

  function handleConfirm() {
    state.open = false
    state.resolve?.(true)
    state.resolve = null
  }

  function handleCancel() {
    state.open = false
    state.resolve?.(false)
    state.resolve = null
  }

  return { confirm, confirmState: state, handleConfirm, handleCancel }
}
