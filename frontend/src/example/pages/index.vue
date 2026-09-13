<route lang="yaml">
meta:
  layout: landing
  requiresAuth: false
</route>

<template>
  <div>
    <!-- ─── HERO ─────────────────────────────────────────────────── -->
    <section class="relative overflow-hidden bg-slate-950 text-white">
      <!-- Subtle grid texture -->
      <div
        class="pointer-events-none absolute inset-0 opacity-[0.06]"
        style="
          background-image:
            linear-gradient(to right, white 1px, transparent 1px),
            linear-gradient(to bottom, white 1px, transparent 1px);
          background-size: 56px 56px;
        "
        aria-hidden="true"
      />
      <div
        class="pointer-events-none absolute inset-x-0 bottom-0 h-40 bg-gradient-to-t from-slate-950 to-transparent"
        aria-hidden="true"
      />

      <div class="container relative max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-24 text-center">
        <!--
          Grid with every variant stacked in one cell: the longest word fixes
          the headline's height, so a word that wraps to an extra line on a
          narrow screen can't shove the rest of the page up and down.
        -->
        <h1
          class="grid text-4xl sm:text-5xl font-semibold tracking-tight text-white leading-[1.1]"
          :aria-label="headlineLabel"
        >
          <span
            v-for="word in headlineWords"
            :key="word"
            class="col-start-1 row-start-1 invisible"
            aria-hidden="true"
          >
            {{ $t('landing.hero.headline', { word }) }}
          </span>
          <i18n-t
            keypath="landing.hero.headline"
            tag="span"
            scope="global"
            class="col-start-1 row-start-1"
          >
            <template #word>
              <RotatingWord :words="headlineWords" class="text-blue-500" />
            </template>
          </i18n-t>
        </h1>

        <p class="mt-6 text-lg text-slate-400 leading-relaxed max-w-2xl mx-auto">
          {{ $t('landing.hero.sub') }}
        </p>

        <div
          class="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3"
        >
          <RouterLink
            to="/register"
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-200 transition-colors"
          >
            {{
              heroTrialDays
                ? $t('landing.hero.ctaButton', { days: heroTrialDays })
                : $t('landing.nav.cta')
            }}
            <ArrowRight class="w-4 h-4" />
          </RouterLink>
          <RouterLink
            :to="localePath('pricing')"
            class="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-6 py-3 text-sm font-medium text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
          >
            {{ $t('landing.nav.pricing') }}
          </RouterLink>
        </div>

        <ul class="mt-8 flex flex-wrap justify-center gap-x-6 gap-y-2 text-xs text-slate-500">
          <li v-for="(point, i) in trustPoints" :key="i" class="inline-flex items-center gap-1.5">
            <Check class="w-3.5 h-3.5 shrink-0 text-slate-600" />
            {{ point }}
          </li>
        </ul>
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

    <!-- ─── FEATURES ─────────────────────────────────────────────── -->
    <section id="features" class="bg-slate-50 py-20 border-b border-slate-200 scroll-mt-16">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6">
        <div class="max-w-2xl">
          <h2 class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
            {{ $t('landing.features.title') }}
          </h2>
          <p class="mt-3 text-slate-500 leading-relaxed">
            {{ $t('landing.features.sub') }}
          </p>
        </div>

        <div class="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-x-8 gap-y-8">
          <div
            v-for="feature in features"
            :key="feature.key"
            class="border-t border-slate-300 pt-4"
          >
            <component :is="feature.icon" class="w-5 h-5 text-slate-400" />
            <h3 class="mt-3 text-sm font-semibold text-slate-900">{{ feature.title }}</h3>
            <p class="mt-1 text-xs text-slate-500 leading-relaxed">{{ feature.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── PRICING ──────────────────────────────────────────────── -->
    <section id="pricing" class="bg-white py-20 border-b border-slate-200 scroll-mt-16">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6">
        <div class="max-w-2xl">
          <h2 class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
            {{ $t('landing.pricing.title') }}
          </h2>
          <p class="mt-3 text-slate-500">{{ $t('landing.pricing.sub') }}</p>
        </div>

        <div class="mt-10">
          <PricingPlans />
        </div>
      </div>
    </section>

    <!-- ─── FAQ ──────────────────────────────────────────────────── -->
    <section id="faq" class="bg-slate-50 py-20 border-b border-slate-200 scroll-mt-16">
      <div
        class="container max-w-6xl mx-auto px-4 sm:px-6 grid lg:grid-cols-[minmax(0,18rem)_minmax(0,1fr)] gap-10"
      >
        <h2
          class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900 lg:sticky lg:top-24 lg:self-start"
        >
          {{ $t('landing.faq.title') }}
        </h2>

        <div class="rounded-xl border border-slate-200 bg-white divide-y divide-slate-200">
          <div v-for="(faq, i) in faqItems" :key="i">
            <button
              type="button"
              class="w-full flex items-start justify-between gap-4 px-5 py-4 text-left"
              :aria-expanded="openFaq === i"
              @click="openFaq = openFaq === i ? null : i"
            >
              <span class="text-sm font-medium text-slate-900">{{ faq.q }}</span>
              <ChevronDown
                class="w-4 h-4 mt-0.5 shrink-0 text-slate-400 transition-transform duration-200"
                :class="openFaq === i ? 'rotate-180' : ''"
              />
            </button>
            <div v-show="openFaq === i" class="px-5 pb-5 text-sm text-slate-500 leading-relaxed">
              {{ faq.a }}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── CTA BANNER ───────────────────────────────────────────── -->
    <section class="bg-slate-950 py-20">
      <div class="container max-w-3xl mx-auto px-4 sm:px-6 text-center">
        <h2 class="text-2xl sm:text-3xl font-semibold tracking-tight text-white">
          {{ $t('landing.ctaBanner.headline') }}
        </h2>
        <div
          class="mt-8 flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3"
        >
          <RouterLink
            to="/register"
            class="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-slate-900 hover:bg-slate-200 transition-colors"
          >
            {{ $t('landing.ctaBanner.button') }}
            <ArrowRight class="w-4 h-4" />
          </RouterLink>
          <RouterLink
            to="/login"
            class="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-6 py-3 text-sm font-medium text-slate-300 hover:border-slate-500 hover:text-white transition-colors"
          >
            {{ $t('landing.nav.login') }}
          </RouterLink>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowRight, Check, ChevronDown, UserPlus, FolderOpen, Rocket } from 'lucide-vue-next'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useFeatureCatalog } from '@/example/composables/useFeatureCatalog'
import { useLocalePath } from '@/platform/composables/useLocalePath'
import type { PlanOut } from '@/platform/types'

const { t, tm, rt } = useI18n()
const { localePath } = useLocalePath()
const subscriptionStore = useSubscriptionStore()
const { features } = useFeatureCatalog()

/** Words the hero headline cycles through - see `landing.hero.headlineWords`. */
const headlineWords = computed(() =>
  (tm('landing.hero.headlineWords') as unknown[]).map((word) =>
    typeof word === 'string' ? word : rt(word as Parameters<typeof rt>[0]),
  ),
)

/** The headline as one fixed sentence, for assistive tech. */
const headlineLabel = computed(() =>
  t('landing.hero.headline', { word: headlineWords.value[0] ?? '' }),
)

const openFaq = ref<number | null>(null)
const plans = ref<PlanOut[]>([])

const heroTrialDays = computed(() => {
  for (const plan of plans.value) {
    const p = plan.prices.find((p) => p.amount > 0 && p.is_active && p.trial_period_days)
    if (p) return p.trial_period_days
  }
  return null
})

const trustPoints = computed(() => [t('landing.hero.socialProof'), t('landing.hero.trustCancel')])

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

const faqItems = computed(() =>
  [1, 2, 3, 4, 5, 6].map((n) => ({ q: t(`landing.faq.q${n}`), a: t(`landing.faq.a${n}`) })),
)

onMounted(async () => {
  plans.value = await subscriptionStore.listPlans()
})
</script>
