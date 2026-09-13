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
          {{ $t('marketing.features.heroTitle') }}
        </h1>
        <p class="mt-5 text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {{ $t('marketing.features.heroSub') }}
        </p>
        <RouterLink
          to="/register"
          class="mt-8 inline-flex items-center gap-2 rounded-xl bg-white px-7 py-3.5 text-sm font-semibold text-slate-900 hover:bg-slate-100 transition-colors shadow-lg"
        >
          {{ $t('landing.nav.cta') }}
          <ArrowRight class="w-4 h-4" />
        </RouterLink>
      </div>
    </section>

    <!-- ─── FEATURES ─────────────────────────────────────────────── -->
    <section class="bg-slate-50 py-20 border-b border-slate-200">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6">
        <div class="max-w-2xl">
          <h2 class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
            {{ $t('landing.features.title') }}
          </h2>
          <p class="mt-3 text-slate-500 leading-relaxed">
            {{ $t('landing.features.sub') }}
          </p>
        </div>

        <div
          class="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-px rounded-xl border border-slate-200 bg-slate-200 overflow-hidden"
        >
          <div v-for="feature in features" :key="feature.key" class="bg-white p-5">
            <component :is="feature.icon" class="w-5 h-5 text-slate-400" />
            <h3 class="mt-3 text-sm font-semibold text-slate-900">{{ feature.title }}</h3>
            <p class="mt-1 text-xs text-slate-500 leading-relaxed">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── HOW IT WORKS ─────────────────────────────────────────── -->
    <section class="bg-white py-20 border-b border-slate-200">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6">
        <h2 class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
          {{ $t('landing.howItWorks.title') }}
        </h2>

        <div class="mt-12 grid grid-cols-1 sm:grid-cols-3 gap-x-10 gap-y-10">
          <div
            v-for="step in howItWorksSteps"
            :key="step.num"
            class="border-t border-slate-900 pt-5"
          >
            <div class="flex items-center gap-2.5">
              <span class="text-xs font-semibold tabular-nums text-slate-600">{{ step.num }}</span>
              <component :is="step.icon" class="w-4 h-4 text-slate-900" />
            </div>
            <h3 class="mt-3 font-semibold text-slate-900">{{ step.title }}</h3>
            <p class="mt-2 text-sm text-slate-500 leading-relaxed">{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── CTA BANNER ───────────────────────────────────────────── -->
    <section class="bg-slate-950 py-20">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6 text-center">
        <h2 class="text-2xl sm:text-4xl font-bold text-white mb-8">
          {{ $t('landing.ctaBanner.headline') }}
        </h2>
        <RouterLink
          to="/register"
          class="inline-flex items-center gap-2 rounded-xl bg-white px-8 py-4 text-sm font-semibold text-slate-900 hover:bg-slate-100 transition-colors shadow-lg"
        >
          {{ $t('landing.ctaBanner.button') }}
          <ArrowRight class="w-4 h-4" />
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowRight, UserPlus, FolderOpen, Rocket } from 'lucide-vue-next'
import { useFeatureCatalog } from '@/example/composables/useFeatureCatalog'

const { t } = useI18n()
const { features } = useFeatureCatalog()

// `num` is derived here rather than from the v-for index so the template holds
// no arithmetic - it also gives each row a stable :key.
const howItWorksSteps = computed(() =>
  [
    {
      icon: UserPlus,
      title: t('landing.howItWorks.step1Title'),
      desc: t('landing.howItWorks.step1Desc'),
    },
    {
      icon: FolderOpen,
      title: t('landing.howItWorks.step2Title'),
      desc: t('landing.howItWorks.step2Desc'),
    },
    {
      icon: Rocket,
      title: t('landing.howItWorks.step3Title'),
      desc: t('landing.howItWorks.step3Desc'),
    },
  ].map((step, i) => ({ ...step, num: String(i + 1).padStart(2, '0') })),
)
</script>
