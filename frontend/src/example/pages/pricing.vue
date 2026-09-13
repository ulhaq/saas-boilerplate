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
          {{ $t('landing.pricing.title') }}
        </h1>
        <p class="mt-5 text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          {{ $t('marketing.pricing.heroSub') }}
        </p>
        <div class="mt-8 flex justify-center">
          <span
            class="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800"
          >
            <ShieldCheck class="w-3.5 h-3.5 shrink-0" />
            {{ $t('landing.hero.socialProof') }}
          </span>
        </div>
      </div>
    </section>

    <!-- ─── PLANS ────────────────────────────────────────────────── -->
    <section class="bg-white py-20 border-b border-slate-100">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6">
        <PricingPlans :heading-level="2" />
      </div>
    </section>

    <!-- ─── FAQ ──────────────────────────────────────────────────── -->
    <section class="bg-slate-50 py-20 border-b border-slate-100">
      <div class="container max-w-3xl mx-auto px-4 sm:px-6">
        <h2 class="text-2xl sm:text-3xl font-bold text-center text-slate-900 mb-12">
          {{ $t('marketing.pricing.faqTitle') }}
        </h2>
        <div class="divide-y divide-slate-100">
          <div v-for="(faq, i) in faqItems" :key="i">
            <button
              type="button"
              class="w-full flex items-center justify-between gap-4 py-5 text-left"
              :aria-expanded="openFaq === i"
              @click="openFaq = openFaq === i ? null : i"
            >
              <span class="font-medium text-slate-900">{{ faq.q }}</span>
              <ChevronDown
                class="w-5 h-5 text-slate-400 flex-shrink-0 transition-transform duration-200"
                :class="openFaq === i ? 'rotate-180' : ''"
              />
            </button>
            <div v-show="openFaq === i" class="pb-5 text-sm text-slate-500 leading-relaxed">
              {{ faq.a }}
            </div>
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
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { ArrowRight, ChevronDown, ShieldCheck } from 'lucide-vue-next'

const { t } = useI18n()

const openFaq = ref<number | null>(null)

// Pricing-specific FAQ, a focused subset of the landing FAQ.
const faqItems = computed(() => [
  { q: t('landing.faq.q3'), a: t('landing.faq.a3') },
  { q: t('landing.faq.q4'), a: t('landing.faq.a4') },
  { q: t('landing.faq.q2'), a: t('landing.faq.a2') },
])
</script>
