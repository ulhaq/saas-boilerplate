<template>
  <span
    ref="root"
    class="relative inline-block whitespace-nowrap"
    :class="reduceMotion ? '' : 'word-box'"
    :style="boxStyle"
  >
    <!--
      Sizer: always the first word, kept in flow so the inline box has a sane
      width before hydration measures the rest (and if JS never runs).
    -->
    <span class="invisible" aria-hidden="true">{{ words[0] }}</span>

    <Transition :name="reduceMotion ? 'word-static' : 'word'">
      <span :key="index" class="absolute left-0 top-0 inline-block whitespace-nowrap">
        {{ words[index] }}
      </span>
    </Transition>
    <!--
      Marks the slot as a changing one, and resizes with each word. `bg-current`
      inherits whatever text colour the call site sets, so this component stays
      colour-neutral.
    -->
    <span
      class="absolute inset-x-0 -bottom-1 h-[5px] rounded-full bg-current opacity-30"
      aria-hidden="true"
    />
  </span>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useMediaQuery } from '@vueuse/core'

const props = withDefaults(
  defineProps<{
    /** Words to cycle through. The first one is what the prerendered HTML shows. */
    words: string[]
    /** Milliseconds each word stays on screen. */
    interval?: number
  }>(),
  { interval: 2600 },
)

const index = ref(0)
const root = ref<HTMLElement | null>(null)
const widths = ref<number[]>([])
const reduceMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

/**
 * Pinning the box to the current word's measured width is what keeps the rest
 * of the sentence from jumping: the width animates alongside the word swap
 * instead of snapping when the new word replaces the old one.
 */
const boxStyle = computed(() => {
  const w = widths.value[index.value]
  return w ? { width: `${w}px` } : undefined
})

/** Measure every word in the live font by probing inside the box itself. */
function measure() {
  const el = root.value
  if (!el) return
  const probe = document.createElement('span')
  probe.style.cssText = 'position:absolute;top:0;left:0;visibility:hidden;white-space:nowrap'
  el.appendChild(probe)
  widths.value = props.words.map((word) => {
    probe.textContent = word
    return probe.getBoundingClientRect().width
  })
  el.removeChild(probe)
}

let timer: ReturnType<typeof setInterval> | undefined

function stop() {
  if (timer) {
    clearInterval(timer)
    timer = undefined
  }
}

function start() {
  stop()
  // Nothing to rotate through, or the visitor asked for less motion - hold on
  // the first word.
  if (props.words.length < 2 || reduceMotion.value) return
  timer = setInterval(() => {
    index.value = (index.value + 1) % props.words.length
  }, props.interval)
}

// Only runs in the browser, so the SSG build emits the first word as static
// text and the rotation starts on hydration.
onMounted(() => {
  measure()
  // Web fonts land after first paint and change every measurement.
  document.fonts?.ready.then(measure).catch(() => {})
  window.addEventListener('resize', measure)
  start()
})

onBeforeUnmount(() => {
  stop()
  window.removeEventListener('resize', measure)
})

// Restart on a language switch (the word list changes) or a motion-preference
// change, and reset if the new list is shorter than the current position.
watch(
  () => [props.words, props.interval, reduceMotion.value] as const,
  async () => {
    if (index.value >= props.words.length) index.value = 0
    await nextTick()
    measure()
    start()
  },
  { deep: true },
)
</script>

<style scoped>
.word-box {
  transition: width 0.35s ease;
}

.word-enter-active,
.word-leave-active {
  transition:
    opacity 0.35s ease,
    transform 0.35s ease;
}

.word-enter-from {
  opacity: 0;
  transform: translateY(0.35em);
}

.word-leave-to {
  opacity: 0;
  transform: translateY(-0.35em);
}
</style>
