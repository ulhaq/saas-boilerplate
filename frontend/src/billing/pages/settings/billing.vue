<route lang="yaml">
meta:
  permission: manage:subscription
  breadcrumb: nav.subscription
</route>

<template>
  <div class="animate-fade-in space-y-6">
    <PageHeader :title="$t('subscription.title')" :description="$t('subscription.description')" />

    <!-- Billing email card -->
    <div v-if="!isLoading && subscription" class="rounded-lg border p-6 space-y-4">
      <div>
        <h3 class="font-semibold text-lg">{{ $t('subscription.billingEmailTitle') }}</h3>
        <p class="text-muted-foreground text-sm mt-0.5">
          {{ $t('subscription.billingEmailDescription') }}
        </p>
      </div>
      <form class="flex flex-col gap-2 sm:flex-row sm:items-end" @submit.prevent="handleSaveEmail">
        <div class="flex-1 space-y-1.5">
          <label for="billing-email" class="text-sm font-medium">{{
            $t('subscription.billingEmailLabel')
          }}</label>
          <Input
            id="billing-email"
            v-model="billingEmail"
            type="email"
            required
            :placeholder="$t('subscription.billingEmailPlaceholder')"
          />
        </div>
        <SaveButton
          :saving="emailSaving"
          :saved="emailSaved"
          :disabled="billingEmail === (subscription.billing_email ?? '')"
        >
          {{ $t('subscription.billingEmailSave') }}
        </SaveButton>
      </form>
    </div>

    <!-- Loading skeleton -->
    <div v-if="isLoading" class="space-y-4">
      <Skeleton class="h-48 w-full rounded-lg" />
    </div>

    <!-- Pending checkout card (incomplete subscription - edge case) -->
    <template v-else-if="subscription?.status === 'incomplete'">
      <div class="rounded-lg border p-6 space-y-4">
        <div>
          <h3 class="font-semibold text-lg">{{ $t('subscription.startSubscriptionTitle') }}</h3>
          <p class="text-muted-foreground text-sm mt-0.5">
            {{ $t('subscription.incompleteNotice') }}
          </p>
        </div>

        <CurrentPrice v-if="subscription.plan_price" :price="subscription.plan_price" />

        <template v-if="subscription.plan_price_id">
          <Button :disabled="isCheckingOut" @click="handleCheckout(subscription.plan_price_id!)">
            <Loader2 v-if="isCheckingOut" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('subscription.subscribe') }}
          </Button>
        </template>
      </div>
    </template>

    <!-- Free plan card (active free subscription - show trial/upgrade CTA) -->
    <template
      v-else-if="subscription?.status === 'active' && subscription.plan_price?.amount === 0"
    >
      <div class="rounded-lg border p-6 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="font-semibold text-lg">
              <Skeleton v-if="plansLoading" class="h-5 w-24 inline-block" />
              <span v-else>{{ planName(subscription.plan_price) || $t('subscription.free') }}</span>
            </h3>
            <p class="text-sm text-muted-foreground mt-0.5">{{ $t('subscription.currentPlan') }}</p>
          </div>
          <Badge :variant="statusBadgeVariant('active')" class="shrink-0">
            {{ $t('subscription.status.active') }}
          </Badge>
        </div>

        <CurrentPrice v-if="subscription.plan_price" :price="subscription.plan_price" />

        <template v-if="subscription.trial_end">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="outline" :disabled="isPortalLoading" @click="handlePortal">
                  <Loader2 v-if="isPortalLoading" class="w-4 h-4 mr-2 animate-spin" />
                  <ExternalLink v-else class="w-4 h-4 mr-2" />
                  {{ $t('subscription.manageBilling') }}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{{ $t('subscription.manageBillingTooltip') }}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </template>
      </div>

      <!-- Trial CTA card - separate from the current plan card -->
      <div
        v-if="!plansLoading && trialPrice && !subscription.trial_used"
        class="rounded-lg border border-primary/20 p-6 space-y-3"
      >
        <div>
          <h3 class="font-semibold text-lg">{{ $t('subscription.startTrialTitle') }}</h3>
          <p class="text-muted-foreground text-sm mt-0.5">
            {{
              $t('subscription.heroTrialSubtitle', {
                days: trialPrice.trial_period_days,
                price: formatPrice(trialPrice),
                interval: trialPrice.interval,
              })
            }}
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-4">
          <Button :disabled="isTrialing" @click="handleTrial(trialPrice.id)">
            <Loader2 v-if="isTrialing" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('subscription.startTrialButton', { days: trialPrice.trial_period_days }) }}
          </Button>
          <span
            class="inline-flex items-center gap-1.5 rounded-full bg-success/10 px-3 py-1 text-xs font-medium text-success"
          >
            <ShieldCheck class="w-3.5 h-3.5 shrink-0" />
            {{ $t('subscription.noCardRequired') }}
          </span>
        </div>
      </div>

      <!-- Plan picker - lets the user choose a specific plan -->
      <div v-if="plansLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="n in 3" :key="n" class="h-36 w-full rounded-lg" />
      </div>
      <div v-else-if="paidPlans.length > 0" class="space-y-3">
        <h3 class="font-semibold">{{ $t('subscription.availablePlans') }}</h3>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PlanCard v-for="plan in paidPlans" :key="plan.id" :plan="plan" :rows="comparisonRows">
            <template #badge>
              <span
                v-if="
                  plan.prices.some((p) => p.amount > 0 && p.is_active && p.trial_period_days) &&
                  !subscription?.trial_used
                "
                class="inline-flex items-center gap-1 rounded-full bg-success/10 px-2 py-0.5 text-xs font-medium text-success shrink-0"
              >
                <ShieldCheck class="w-3 h-3 shrink-0" />
                {{ $t('subscription.noCardRequired') }}
              </span>
            </template>
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <PriceLabel :price="price" free-as-text />
                <Button v-if="price.amount === 0" size="sm" disabled>
                  {{ $t('subscription.currentPlan') }}
                </Button>
                <Button
                  v-else-if="price.trial_period_days && !subscription.trial_used"
                  size="sm"
                  :disabled="trialId === price.id || isTrialing"
                  @click="handleTrial(price.id)"
                >
                  <Loader2 v-if="trialId === price.id" class="w-4 h-4 mr-2 animate-spin" />
                  {{ $t('subscription.startTrialButton', { days: price.trial_period_days }) }}
                </Button>
                <Button
                  v-else
                  size="sm"
                  :disabled="checkoutId === price.id || isCheckingOut"
                  @click="handleCheckout(price.id)"
                >
                  <Loader2 v-if="checkoutId === price.id" class="w-4 h-4 mr-2 animate-spin" />
                  {{ $t('subscription.subscribe') }}
                </Button>
              </div>
            </div>
          </PlanCard>
        </div>
      </div>
    </template>

    <!-- Paused card (trial ended, no payment method) -->
    <template v-else-if="subscription?.status === 'paused'">
      <div class="rounded-lg border p-6 space-y-4">
        <div>
          <h3 class="font-semibold text-lg">{{ $t('subscription.trialEndedTitle') }}</h3>
          <p class="text-muted-foreground text-sm mt-0.5">
            <Skeleton v-if="plansLoading" class="h-4 w-96 inline-block" />
            <span v-else>{{
              $t('subscription.trialEndedDescription', { plan: planName(subscription.plan_price) })
            }}</span>
          </p>
        </div>

        <CurrentPrice v-if="subscription.plan_price" :price="subscription.plan_price" />

        <Button :disabled="isPortalLoading" @click="handlePortal">
          <Loader2 v-if="isPortalLoading" class="w-4 h-4 mr-2 animate-spin" />
          <CreditCard v-else class="w-4 h-4 mr-2" />
          {{ $t('subscription.addPaymentMethod') }}
        </Button>
      </div>

      <!-- Available paid plans to subscribe to from the paused state -->
      <div v-if="paidPlans.length > 0" class="space-y-3">
        <h3 class="font-semibold">{{ $t('subscription.availablePlans') }}</h3>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PlanCard v-for="plan in paidPlans" :key="plan.id" :plan="plan" :rows="comparisonRows">
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active && p.amount > 0)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <PriceLabel :price="price" />
                <Button
                  size="sm"
                  :disabled="switchId === price.id || price.id === subscription?.plan_price_id"
                  @click="handleSwitchPlan(price.id, price.amount)"
                >
                  <Loader2 v-if="switchId === price.id" class="w-4 h-4 mr-2 animate-spin" />
                  {{
                    price.id === subscription?.plan_price_id
                      ? $t('subscription.currentPlan')
                      : $t('subscription.subscribe')
                  }}
                </Button>
              </div>
            </div>
          </PlanCard>
        </div>
      </div>
    </template>

    <!-- Active subscription card -->
    <template v-else-if="subscription">
      <div class="rounded-lg border p-6 space-y-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="font-semibold text-lg">
              <Skeleton v-if="plansLoading" class="h-5 w-24 inline-block" />
              <span v-else>{{
                subscription.plan_price
                  ? planName(subscription.plan_price)
                  : $t('subscription.unknownPlan')
              }}</span>
            </h3>
            <p class="text-sm text-muted-foreground mt-0.5">{{ $t('subscription.currentPlan') }}</p>
          </div>
          <Badge :variant="statusBadgeVariant(subscription.status)" class="shrink-0">
            {{ $t(`subscription.status.${subscription.status}`) }}
          </Badge>
        </div>

        <!-- Trial-ending banner -->
        <div v-if="subscription.status === 'trialing' && subscription.trial_end">
          <!-- No payment method yet -->
          <div
            v-if="!subscription.has_payment_method"
            class="rounded-md border border-warning/20 bg-warning/10 px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          >
            <p class="text-sm text-warning">
              {{ $t('subscription.trialEndsIn', { date: formatDateTime(subscription.trial_end) }) }}
            </p>
            <Button
              size="sm"
              class="shrink-0 bg-warning hover:bg-warning/90 text-warning-foreground"
              :disabled="isPortalLoading"
              @click="handlePortal"
            >
              <Loader2 v-if="isPortalLoading" class="w-3.5 h-3.5 mr-1.5 animate-spin" />
              <CreditCard v-else class="w-3.5 h-3.5 mr-1.5" />
              {{ $t('subscription.addPaymentMethod') }}
            </Button>
          </div>
          <!-- Payment method already on file -->
          <div v-else class="rounded-md border border-success/20 bg-success/10 px-4 py-3">
            <p class="text-sm text-success">
              {{
                $t('subscription.trialEndsAllSet', { date: formatDateTime(subscription.trial_end) })
              }}
            </p>
          </div>
        </div>

        <!-- Cancellation pending banner -->
        <div
          v-if="subscription.cancel_at_period_end && subscription.current_period_end"
          class="rounded-md border border-warning/20 bg-warning/10 px-4 py-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"
        >
          <p class="text-sm text-warning">
            {{
              $t('subscription.cancelPending', {
                date: formatDate(subscription.current_period_end),
              })
            }}
          </p>
          <button
            class="text-sm font-medium text-warning underline whitespace-nowrap"
            :disabled="isActing"
            @click="handleResume"
          >
            {{ $t('subscription.resumeSubscription') }}
          </button>
        </div>

        <CurrentPrice v-if="subscription.plan_price" :price="subscription.plan_price" />

        <p
          v-if="subscription.current_period_end && !subscription.cancel_at_period_end"
          class="text-sm text-muted-foreground"
        >
          {{ $t('subscription.renewsOn', { date: formatDate(subscription.current_period_end) }) }}
        </p>

        <div class="flex gap-2 flex-wrap">
          <Button
            v-if="subscription.cancel_at_period_end"
            :disabled="isActing"
            @click="handleResume"
          >
            <Loader2 v-if="isActing" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('subscription.resumeSubscription') }}
          </Button>
          <Button v-else variant="outline" :disabled="isActing" @click="handleCancel">
            <Loader2 v-if="isActing" class="w-4 h-4 mr-2 animate-spin" />
            {{ $t('subscription.cancelSubscription') }}
          </Button>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger as-child>
                <Button variant="outline" :disabled="isPortalLoading" @click="handlePortal">
                  <Loader2 v-if="isPortalLoading" class="w-4 h-4 mr-2 animate-spin" />
                  <ExternalLink v-else class="w-4 h-4 mr-2" />
                  {{ $t('subscription.manageBilling') }}
                </Button>
              </TooltipTrigger>
              <TooltipContent>{{ $t('subscription.manageBillingTooltip') }}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      <!-- Available paid plans for upgrading/downgrading.
           Free plan is excluded - to return to free, cancel the subscription. -->
      <div v-if="paidPlans.length > 0" class="space-y-3">
        <h3 class="font-semibold">{{ $t('subscription.availablePlans') }}</h3>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PlanCard v-for="plan in paidPlans" :key="plan.id" :plan="plan" :rows="comparisonRows">
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active && p.amount > 0)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <PriceLabel :price="price" />
                <Button
                  size="sm"
                  :disabled="switchId === price.id || price.id === subscription?.plan_price_id"
                  @click="handleSwitchPlan(price.id, price.amount)"
                >
                  <Loader2 v-if="switchId === price.id" class="w-4 h-4 mr-2 animate-spin" />
                  {{
                    price.id === subscription?.plan_price_id
                      ? $t('subscription.currentPlan')
                      : subscription?.plan_price &&
                          monthlyEquivalent(price) > monthlyEquivalent(subscription.plan_price)
                        ? $t('subscription.upgrade')
                        : $t('subscription.downgrade')
                  }}
                </Button>
              </div>
            </div>
          </PlanCard>
        </div>
      </div>
    </template>

    <!-- No subscription - show plan selection -->
    <template v-else>
      <div class="rounded-lg border p-6 space-y-4">
        <div>
          <h3 class="font-semibold text-lg">{{ $t('subscription.noSubscription') }}</h3>
          <p class="text-muted-foreground text-sm mt-0.5">{{ $t('subscription.choosePlan') }}</p>
        </div>

        <div v-if="plansLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Skeleton v-for="n in 3" :key="n" class="h-36 w-full rounded-lg" />
        </div>
        <p v-else-if="availablePlans.length === 0" class="text-sm text-muted-foreground">
          {{ $t('subscription.noPlansAvailable') }}
        </p>
        <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <PlanCard
            v-for="plan in availablePlans"
            :key="plan.id"
            :plan="plan"
            :rows="comparisonRows"
          >
            <p
              v-if="plan.prices.filter((p) => p.is_active).length === 0"
              class="text-xs text-muted-foreground"
            >
              {{ $t('subscription.noPricesAvailable') }}
            </p>
            <div v-else class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <PriceLabel :price="price" />
                <Button
                  size="sm"
                  :disabled="checkoutId === price.id || isCheckingOut"
                  @click="handleCheckout(price.id)"
                >
                  <Loader2 v-if="checkoutId === price.id" class="w-4 h-4 mr-2 animate-spin" />
                  {{ $t('subscription.subscribe') }}
                </Button>
              </div>
            </div>
          </PlanCard>
        </div>
      </div>
    </template>

    <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { Loader2, ExternalLink, ShieldCheck, CreditCard } from 'lucide-vue-next'
import { Button } from '@/platform/components/ui/button'
import { Badge } from '@/platform/components/ui/badge'
import { Input } from '@/platform/components/ui/input'
import { Skeleton } from '@/platform/components/ui/skeleton'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/platform/components/ui/tooltip'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import CurrentPrice from '@/billing/components/CurrentPrice.vue'
import PlanCard from '@/billing/components/PlanCard.vue'
import PriceLabel from '@/billing/components/PriceLabel.vue'
import { useBillingFormat } from '@/billing/composables/useBillingFormat'
import { useBillingPage } from '@/billing/composables/useBillingPage'
import { useFormatDate } from '@/platform/composables/useFormatDate'

const { formatDate, formatDateTime } = useFormatDate()
const { formatPrice, monthlyEquivalent, statusBadgeVariant } = useBillingFormat()
const {
  isLoading,
  plansLoading,
  isActing,
  isPortalLoading,
  checkoutId,
  isCheckingOut,
  isTrialing,
  trialId,
  switchId,
  emailSaving,
  emailSaved,
  billingEmail,
  subscription,
  availablePlans,
  errorMessage,
  trialPrice,
  paidPlans,
  comparisonRows,
  planName,
  handleCancel,
  handleResume,
  handlePortal,
  handleSwitchPlan,
  handleTrial,
  handleSaveEmail,
  handleCheckout,
} = useBillingPage()
</script>
