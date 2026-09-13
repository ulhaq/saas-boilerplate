<template>
  <div>
    <!-- Loading skeleton -->
    <div v-if="plansLoading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div
        v-for="n in 4"
        :key="n"
        class="rounded-2xl border border-slate-200 bg-white p-6 animate-pulse space-y-4"
      >
        <div class="h-5 bg-slate-200 rounded w-20" />
        <div class="h-8 bg-slate-200 rounded w-24" />
        <div class="space-y-2.5 pt-2">
          <div v-for="r in 5" :key="r" class="h-4 bg-slate-100 rounded" />
        </div>
        <div class="h-10 bg-slate-200 rounded-xl mt-4" />
      </div>
    </div>

    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
      <div
        v-for="plan in pricingPlans"
        :key="plan.id"
        class="rounded-2xl border p-6 flex flex-col transition-all"
        :class="
          plan.recommended
            ? 'border-slate-900 bg-slate-900 text-white shadow-xl'
            : 'border-slate-200 bg-white hover:shadow-md'
        "
      >
        <div class="flex items-center justify-between">
          <component
            :is="heading"
            class="font-bold text-lg"
            :class="plan.recommended ? 'text-white' : 'text-slate-900'"
          >
            {{ plan.name }}
          </component>
          <span
            v-if="plan.isFree"
            class="inline-flex rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800"
          >
            {{ $t('landing.pricing.forever') }}
          </span>
          <span
            v-if="plan.recommended"
            class="text-xs font-semibold text-emerald-400 uppercase tracking-wide"
          >
            {{ $t('landing.pricing.recommended') }}
          </span>
        </div>
        <div class="mt-3 flex items-end gap-1">
          <span
            class="text-3xl font-bold"
            :class="plan.recommended ? 'text-white' : 'text-slate-900'"
          >
            {{ plan.price }}
          </span>
          <span class="text-sm mb-1 text-slate-400">
            {{ $t('landing.pricing.monthly') }}
          </span>
        </div>

        <ul class="mt-6 space-y-3 flex-1">
          <li
            v-for="item in plan.highlights"
            :key="item.label"
            class="flex items-start gap-2.5 text-sm"
          >
            <Check
              class="w-4 h-4 flex-shrink-0 mt-0.5"
              :class="plan.recommended ? 'text-emerald-400' : 'text-emerald-500'"
            />
            <span
              class="inline-flex items-center gap-1 flex-wrap"
              :class="plan.recommended ? 'text-slate-200' : 'text-slate-700'"
            >
              <strong
                v-if="item.value"
                :class="plan.recommended ? 'text-white' : 'text-slate-900'"
                >{{ item.value }}</strong
              >
              <template v-if="item.type === 'feature'">{{ item.label }}</template>
              <Popover v-if="item.details.length">
                <PopoverTrigger as-child>
                  <button
                    class="transition-colors"
                    :class="
                      plan.recommended
                        ? 'text-slate-400 hover:text-slate-200'
                        : 'text-slate-300 hover:text-slate-500'
                    "
                    :aria-label="t('landing.pricing.moreAbout', { feature: item.label })"
                  >
                    <Info class="w-3 h-3" aria-hidden="true" />
                  </button>
                </PopoverTrigger>
                <PopoverContent class="w-56 p-3 bg-white border-slate-200" align="start">
                  <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    {{ item.label }}
                  </p>
                  <ul class="space-y-1">
                    <li
                      v-for="detail in item.details"
                      :key="detail"
                      class="flex items-center gap-1.5 text-xs text-slate-600"
                    >
                      <Check class="w-3 h-3 shrink-0 text-green-600" />
                      {{ detail }}
                    </li>
                  </ul>
                </PopoverContent>
              </Popover>
            </span>
          </li>
        </ul>

        <RouterLink
          to="/register"
          class="mt-8 block text-center rounded-xl py-2.5 text-sm font-semibold transition-colors"
          :class="
            plan.recommended
              ? 'bg-white text-slate-900 hover:bg-slate-100'
              : 'bg-slate-900 text-white hover:bg-slate-700'
          "
        >
          {{
            plan.isFree || !plan.trialDays
              ? $t('landing.pricing.ctaFree')
              : $t('landing.pricing.cta', { days: plan.trialDays })
          }}
        </RouterLink>
      </div>
    </div>

    <!-- Custom plan prompt -->
    <p v-if="!plansLoading" class="mt-8 text-center text-sm text-slate-500">
      {{ $t('landing.pricing.customText') }}
      <RouterLink :to="localePath('contact')" class="font-semibold text-slate-900 hover:underline">
        {{ $t('landing.pricing.customLink') }}
      </RouterLink>
    </p>

    <!-- Comparison Table -->
    <div v-if="!plansLoading && comparisonRows.length" class="mt-16">
      <component :is="heading" class="text-center text-xl font-bold text-slate-900 mb-8">
        {{ $t('landing.pricing.compareTitle') }}
      </component>

      <div class="overflow-x-auto rounded-2xl border border-slate-200">
        <table class="w-full text-sm border-collapse">
          <thead>
            <tr>
              <th
                class="py-4 px-6 text-left bg-slate-50 border-b border-slate-200 font-bold text-slate-600 uppercase tracking-wide rounded-tl-2xl"
              >
                {{ $t('landing.pricing.compareFeature') }}
              </th>
              <th
                v-for="plan in pricingPlans"
                :key="plan.id"
                class="py-4 px-4 text-center border-b last:rounded-tr-2xl"
                :class="
                  plan.recommended
                    ? 'bg-slate-900 border-slate-700'
                    : 'bg-slate-50 border-slate-200'
                "
              >
                <div
                  class="font-bold text-base"
                  :class="plan.recommended ? 'text-white' : 'text-slate-900'"
                >
                  {{ plan.name }}
                </div>
                <div
                  class="text-xs mt-0.5"
                  :class="plan.recommended ? 'text-slate-400' : 'text-slate-500'"
                >
                  {{ plan.price }}
                </div>
                <div
                  v-if="!plan.isFree"
                  class="text-xs mt-0.5"
                  :class="plan.recommended ? 'text-slate-400' : 'text-slate-500'"
                >
                  {{ $t('common.exclVat') }}
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, i) in comparisonRows"
              :key="i"
              class="border-b border-slate-100 last:border-0"
              :class="i % 2 !== 0 ? 'bg-slate-50/60' : ''"
            >
              <td
                class="py-3.5 px-6 font-medium text-slate-700"
                :class="i % 2 !== 0 ? 'bg-slate-50/60' : 'bg-white'"
              >
                <span class="inline-flex items-center gap-1.5">
                  {{ row.label }}
                  <Popover v-if="row.details?.length">
                    <PopoverTrigger as-child>
                      <button
                        class="text-slate-300 hover:text-slate-500 transition-colors"
                        :aria-label="t('landing.pricing.moreAbout', { feature: row.label })"
                      >
                        <Info class="w-3 h-3" aria-hidden="true" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent class="w-56 p-3 bg-white border-slate-200" align="start">
                      <p class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        {{ row.label }}
                      </p>
                      <ul class="space-y-1">
                        <li
                          v-for="detail in row.details"
                          :key="detail"
                          class="flex items-center gap-1.5 text-xs text-slate-600"
                        >
                          <Check class="w-3 h-3 shrink-0 text-green-600" />
                          {{ detail }}
                        </li>
                      </ul>
                    </PopoverContent>
                  </Popover>
                </span>
              </td>
              <td
                v-for="plan in pricingPlans"
                :key="plan.id"
                class="py-3.5 px-4 text-center"
                :class="
                  plan.recommended
                    ? 'bg-slate-900/[0.03]'
                    : i % 2 !== 0
                      ? 'bg-slate-50/60'
                      : 'bg-white'
                "
              >
                <Check v-if="row[plan.name] === true" class="w-4 h-4 mx-auto text-emerald-500" />
                <span
                  v-else-if="row[plan.name] === false"
                  class="text-slate-300 text-base leading-none select-none"
                  >X</span
                >
                <span
                  v-else
                  class="font-semibold"
                  :class="plan.recommended ? 'text-slate-900' : 'text-slate-700'"
                >
                  {{ row[plan.name] }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { useLocalePath } from '@/platform/composables/useLocalePath'
import { Check, Info } from 'lucide-vue-next'
import { Popover, PopoverTrigger, PopoverContent } from '@/platform/components/ui/popover'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import type { PlanOut } from '@/platform/types'

// Embedded under an <h1> on the pricing page but under an <h2> on the landing
// page, so the caller says which level its headings sit at.
const props = withDefaults(defineProps<{ headingLevel?: 2 | 3 }>(), { headingLevel: 3 })
const heading = computed(() => `h${props.headingLevel}` as 'h2' | 'h3')

const { t, tm, locale } = useI18n()
const { localePath } = useLocalePath()
const subscriptionStore = useSubscriptionStore()

const plans = ref<PlanOut[]>([])
const plansLoading = ref(true)

type ComparisonRow = {
  label: string
  stat?: boolean
  details?: string[]
  [planName: string]: string | boolean | string[] | undefined
}

const comparisonRows = computed(() => (tm('planComparisonRows') as ComparisonRow[]) ?? [])

function formatPlanPrice(plan: PlanOut): string {
  const price = plan.prices.find((p) => p.interval === 'month' && p.is_active)
  if (!price) return '-'
  return new Intl.NumberFormat(locale.value, {
    style: 'currency',
    currency: price.currency.toUpperCase(),
    maximumFractionDigits: 0,
  }).format(price.amount / 100)
}

// Plan highlighted as "most popular" in the pricing grid; empty for none.
const POPULAR_PLAN_NAME = ''

const pricingPlans = computed(() =>
  plans.value.map((plan) => {
    const trialPrice = plan.prices.find((p) => p.amount > 0 && p.is_active && p.trial_period_days)
    const statRows = comparisonRows.value.filter((row) => row.stat)
    const featureRows = comparisonRows.value.filter((row) => !row.stat)

    // Stat rows always shown; boolean features only on the plan that first unlocks them
    const highlights = [
      ...statRows.map((row) => ({
        type: 'stat' as const,
        value: typeof row[plan.name] === 'string' ? (row[plan.name] as string) : '',
        label: row.label,
        details: [] as string[],
      })),
      ...featureRows
        .filter((row) => row[plan.name] !== false && plans.value.some((p) => row[p.name] === false))
        .map((row) => ({
          type: 'feature' as const,
          value: '',
          label: row.label,
          details: row.details ?? [],
        })),
    ]

    return {
      id: plan.id,
      name: plan.name,
      price: formatPlanPrice(plan),
      isFree: plan.prices.some((p) => p.amount === 0),
      trialDays: trialPrice?.trial_period_days ?? null,
      recommended: plan.name === POPULAR_PLAN_NAME,
      highlights,
    }
  }),
)

onMounted(async () => {
  try {
    plans.value = await subscriptionStore.listPlans()
  } finally {
    plansLoading.value = false
  }
})
</script>
