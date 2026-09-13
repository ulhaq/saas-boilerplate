<route lang="yaml">
meta:
  layout: landing
  requiresAuth: false
</route>

<template>
  <div>
    <!-- ─── HERO ─────────────────────────────────────────────────── -->
    <section class="bg-slate-950 text-white">
      <div class="container max-w-4xl mx-auto px-4 sm:px-6 pt-20 pb-16 text-center">
        <h1 class="text-4xl sm:text-5xl font-bold tracking-tight text-white leading-tight">
          {{ $t('marketing.about.heroTitle') }}
        </h1>
        <p class="mt-5 text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {{ $t('marketing.about.heroSub') }}
        </p>
      </div>
    </section>

    <!-- ─── MISSION ──────────────────────────────────────────────── -->
    <section class="bg-white py-20 border-b border-slate-100">
      <div class="container max-w-3xl mx-auto px-4 sm:px-6">
        <h2 class="text-2xl sm:text-3xl font-bold text-slate-900 mb-5">
          {{ $t('marketing.about.missionTitle') }}
        </h2>
        <p class="text-slate-600 leading-relaxed mb-4">{{ $t('marketing.about.missionP1') }}</p>
        <p class="text-slate-600 leading-relaxed">{{ $t('marketing.about.missionP2') }}</p>
      </div>
    </section>

    <!-- ─── VALUES ───────────────────────────────────────────────── -->
    <section class="bg-slate-50 py-20 border-b border-slate-100">
      <div class="container max-w-5xl mx-auto px-4 sm:px-6">
        <h2 class="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-14">
          {{ $t('marketing.about.valuesTitle') }}
        </h2>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div
            v-for="(value, i) in values"
            :key="i"
            class="rounded-xl border border-slate-200 bg-white p-6 text-center"
          >
            <div
              class="w-11 h-11 mx-auto rounded-xl bg-slate-900 flex items-center justify-center mb-4"
            >
              <component :is="value.icon" class="w-5 h-5 text-white" />
            </div>
            <h3 class="font-semibold text-slate-900 mb-2">{{ value.title }}</h3>
            <p class="text-sm text-slate-500 leading-relaxed">{{ value.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── CONTACT PROMPT ───────────────────────────────────────── -->
    <section class="bg-white py-20 border-b border-slate-100">
      <div class="container max-w-3xl mx-auto px-4 sm:px-6 text-center">
        <h2 class="text-xl sm:text-2xl font-bold text-slate-900 mb-4">
          {{ $t('marketing.about.contactTitle') }}
        </h2>
        <p class="text-slate-500 mb-6">{{ $t('marketing.about.contactSub') }}</p>
        <RouterLink
          :to="localePath('contact')"
          class="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-7 py-3.5 text-sm font-semibold text-white hover:bg-slate-700 transition-colors"
        >
          {{ $t('landing.footer.contact') }}
          <ArrowRight class="w-4 h-4" />
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useLocalePath } from '@/platform/composables/useLocalePath'
import { RouterLink } from 'vue-router'
import { ArrowRight, ShieldCheck, Zap, Heart } from 'lucide-vue-next'

const { t } = useI18n()
const { localePath } = useLocalePath()

const values = computed(() => [
  {
    icon: Heart,
    title: t('marketing.about.value1Title'),
    desc: t('marketing.about.value1Desc'),
  },
  {
    icon: ShieldCheck,
    title: t('marketing.about.value2Title'),
    desc: t('marketing.about.value2Desc'),
  },
  {
    icon: Zap,
    title: t('marketing.about.value3Title'),
    desc: t('marketing.about.value3Desc'),
  },
])
</script>
