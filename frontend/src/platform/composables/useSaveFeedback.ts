import { ref, onUnmounted } from 'vue'

/**
 * Tracks the lifecycle of a save action so a button can show an inline spinner
 * while running and a transient "Saved" confirmation when it succeeds - instead
 * of firing a toast.
 *
 * Wrap the async work in `save()`; `saving` is true while it runs and `saved`
 * flips true on success, then clears itself after `resetMs`. Errors propagate
 * so callers keep their own try/catch for field/error handling.
 *
 * @example
 * const { saving, saved, save } = useSaveFeedback()
 * await save(() => profileStore.updateMe(payload))
 */
export function useSaveFeedback(resetMs = 2000) {
  const saving = ref(false)
  const saved = ref(false)
  let timer: ReturnType<typeof setTimeout> | undefined

  async function save<T>(fn: () => Promise<T>): Promise<T> {
    if (timer) clearTimeout(timer)
    saved.value = false
    saving.value = true
    try {
      const result = await fn()
      saved.value = true
      timer = setTimeout(() => {
        saved.value = false
      }, resetMs)
      return result
    } finally {
      saving.value = false
    }
  }

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return { saving, saved, save }
}
