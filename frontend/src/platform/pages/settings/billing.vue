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

        <div v-if="subscription.plan_price" class="text-xl font-semibold">
          {{ formatPrice(subscription.plan_price) }}
          <span class="text-sm font-normal text-muted-foreground"
            >/ {{ subscription.plan_price.interval }}</span
          >
          <span
            v-if="subscription.plan_price.amount > 0"
            class="block text-xs font-normal text-muted-foreground"
            >{{ $t('common.exclVat') }}</span
          >
        </div>

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

        <div v-if="subscription.plan_price" class="text-xl font-semibold">
          {{ formatPrice(subscription.plan_price) }}
          <span class="text-sm font-normal text-muted-foreground"
            >/ {{ subscription.plan_price.interval }}</span
          >
        </div>

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
          <div v-for="plan in paidPlans" :key="plan.id" class="rounded-lg border p-4 space-y-3">
            <div class="flex items-start justify-between gap-2">
              <div>
                <h4 class="font-semibold">{{ plan.name }}</h4>
                <p class="text-xs text-muted-foreground mt-0.5">
                  {{ $t(`planDescriptions.${plan.name}`, plan.description) }}
                </p>
              </div>
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
            </div>
            <ul v-if="comparisonRows.length" class="space-y-1.5">
              <li
                v-for="row in comparisonRows"
                :key="row.label"
                class="flex items-center gap-1.5 text-xs"
                :class="row[plan.name] === false ? 'opacity-40' : ''"
              >
                <Check v-if="row[plan.name] !== false" class="w-3 h-3 shrink-0 text-success" />
                <Minus v-else class="w-3 h-3 shrink-0" />
                <span class="text-muted-foreground inline-flex items-center gap-1">
                  <span
                    v-if="typeof row[plan.name] === 'string'"
                    class="font-medium text-foreground"
                    >{{ row[plan.name] }}</span
                  >
                  <template v-if="!row.stat">{{ row.label }}</template>
                  <Popover v-if="row.details?.length">
                    <PopoverTrigger as-child>
                      <button
                        class="text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                      >
                        <Info class="w-3 h-3" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent class="w-56 p-3" align="start">
                      <p
                        class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2"
                      >
                        {{ row.label }}
                      </p>
                      <ul v-if="row.details?.length" class="space-y-1">
                        <li
                          v-for="detail in row.details"
                          :key="detail"
                          class="text-xs text-muted-foreground"
                        >
                          {{ detail }}
                        </li>
                      </ul>
                    </PopoverContent>
                  </Popover>
                </span>
              </li>
            </ul>
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <div>
                  <span class="text-sm font-medium">{{
                    price.amount === 0 ? $t('subscription.free') : formatPrice(price)
                  }}</span>
                  <span v-if="price.amount > 0" class="text-xs text-muted-foreground">
                    / {{ price.interval }}</span
                  >
                  <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
                    $t('common.exclVat')
                  }}</span>
                </div>
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
          </div>
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

        <div v-if="subscription.plan_price" class="text-xl font-semibold">
          {{ formatPrice(subscription.plan_price) }}
          <span class="text-sm font-normal text-muted-foreground"
            >/ {{ subscription.plan_price.interval }}</span
          >
          <span
            v-if="subscription.plan_price.amount > 0"
            class="block text-xs font-normal text-muted-foreground"
            >{{ $t('common.exclVat') }}</span
          >
        </div>

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
          <div v-for="plan in paidPlans" :key="plan.id" class="rounded-lg border p-4 space-y-3">
            <div>
              <h4 class="font-semibold">{{ plan.name }}</h4>
              <p v-if="plan.description" class="text-xs text-muted-foreground mt-0.5">
                {{ $t(`planDescriptions.${plan.name}`, plan.description) }}
              </p>
            </div>
            <ul v-if="comparisonRows.length" class="space-y-1.5">
              <li
                v-for="row in comparisonRows"
                :key="row.label"
                class="flex items-center gap-1.5 text-xs"
                :class="row[plan.name] === false ? 'opacity-40' : ''"
              >
                <Check v-if="row[plan.name] !== false" class="w-3 h-3 shrink-0 text-success" />
                <Minus v-else class="w-3 h-3 shrink-0" />
                <span class="text-muted-foreground inline-flex items-center gap-1">
                  <span
                    v-if="typeof row[plan.name] === 'string'"
                    class="font-medium text-foreground"
                    >{{ row[plan.name] }}</span
                  >
                  <template v-if="!row.stat">{{ row.label }}</template>
                  <Popover v-if="row.details?.length">
                    <PopoverTrigger as-child>
                      <button
                        class="text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                      >
                        <Info class="w-3 h-3" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent class="w-56 p-3" align="start">
                      <p
                        class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2"
                      >
                        {{ row.label }}
                      </p>
                      <ul v-if="row.details?.length" class="space-y-1">
                        <li
                          v-for="detail in row.details"
                          :key="detail"
                          class="text-xs text-muted-foreground"
                        >
                          {{ detail }}
                        </li>
                      </ul>
                    </PopoverContent>
                  </Popover>
                </span>
              </li>
            </ul>
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active && p.amount > 0)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <div>
                  <span class="text-sm font-medium">{{ formatPrice(price) }}</span>
                  <span class="text-xs text-muted-foreground"> / {{ price.interval }}</span>
                  <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
                    $t('common.exclVat')
                  }}</span>
                </div>
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
          </div>
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

        <div v-if="subscription.plan_price" class="text-xl font-semibold">
          {{ formatPrice(subscription.plan_price) }}
          <span class="text-sm font-normal text-muted-foreground"
            >/ {{ subscription.plan_price.interval }}</span
          >
          <span
            v-if="subscription.plan_price.amount > 0"
            class="block text-xs font-normal text-muted-foreground"
            >{{ $t('common.exclVat') }}</span
          >
        </div>

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
          <div v-for="plan in paidPlans" :key="plan.id" class="rounded-lg border p-4 space-y-3">
            <div>
              <h4 class="font-semibold">{{ plan.name }}</h4>
              <p v-if="plan.description" class="text-xs text-muted-foreground mt-0.5">
                {{ $t(`planDescriptions.${plan.name}`, plan.description) }}
              </p>
            </div>
            <ul v-if="comparisonRows.length" class="space-y-1.5">
              <li
                v-for="row in comparisonRows"
                :key="row.label"
                class="flex items-center gap-1.5 text-xs"
                :class="row[plan.name] === false ? 'opacity-40' : ''"
              >
                <Check v-if="row[plan.name] !== false" class="w-3 h-3 shrink-0 text-success" />
                <Minus v-else class="w-3 h-3 shrink-0" />
                <span class="text-muted-foreground inline-flex items-center gap-1">
                  <span
                    v-if="typeof row[plan.name] === 'string'"
                    class="font-medium text-foreground"
                    >{{ row[plan.name] }}</span
                  >
                  <template v-if="!row.stat">{{ row.label }}</template>
                  <Popover v-if="row.details?.length">
                    <PopoverTrigger as-child>
                      <button
                        class="text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                      >
                        <Info class="w-3 h-3" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent class="w-56 p-3" align="start">
                      <p
                        class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2"
                      >
                        {{ row.label }}
                      </p>
                      <ul v-if="row.details?.length" class="space-y-1">
                        <li
                          v-for="detail in row.details"
                          :key="detail"
                          class="text-xs text-muted-foreground"
                        >
                          {{ detail }}
                        </li>
                      </ul>
                    </PopoverContent>
                  </Popover>
                </span>
              </li>
            </ul>
            <div class="space-y-2">
              <div
                v-for="price in plan.prices.filter((p) => p.is_active && p.amount > 0)"
                :key="price.id"
                class="flex items-center justify-between gap-2"
              >
                <div>
                  <span class="text-sm font-medium">{{ formatPrice(price) }}</span>
                  <span class="text-xs text-muted-foreground"> / {{ price.interval }}</span>
                  <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
                    $t('common.exclVat')
                  }}</span>
                </div>
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
          </div>
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
          <div
            v-for="plan in availablePlans"
            :key="plan.id"
            class="rounded-lg border p-4 space-y-3"
          >
            <div>
              <h4 class="font-semibold">{{ plan.name }}</h4>
              <p v-if="plan.description" class="text-xs text-muted-foreground mt-0.5">
                {{ $t(`planDescriptions.${plan.name}`, plan.description) }}
              </p>
            </div>
            <ul v-if="comparisonRows.length" class="space-y-1.5">
              <li
                v-for="row in comparisonRows"
                :key="row.label"
                class="flex items-center gap-1.5 text-xs"
                :class="row[plan.name] === false ? 'opacity-40' : ''"
              >
                <Check v-if="row[plan.name] !== false" class="w-3 h-3 shrink-0 text-success" />
                <Minus v-else class="w-3 h-3 shrink-0" />
                <span class="text-muted-foreground inline-flex items-center gap-1">
                  <span
                    v-if="typeof row[plan.name] === 'string'"
                    class="font-medium text-foreground"
                    >{{ row[plan.name] }}</span
                  >
                  <template v-if="!row.stat">{{ row.label }}</template>
                  <Popover v-if="row.details?.length">
                    <PopoverTrigger as-child>
                      <button
                        class="text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                      >
                        <Info class="w-3 h-3" />
                      </button>
                    </PopoverTrigger>
                    <PopoverContent class="w-56 p-3" align="start">
                      <p
                        class="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2"
                      >
                        {{ row.label }}
                      </p>
                      <ul v-if="row.details?.length" class="space-y-1">
                        <li
                          v-for="detail in row.details"
                          :key="detail"
                          class="text-xs text-muted-foreground"
                        >
                          {{ detail }}
                        </li>
                      </ul>
                    </PopoverContent>
                  </Popover>
                </span>
              </li>
            </ul>
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
                <div>
                  <span class="text-sm font-medium">{{ formatPrice(price) }}</span>
                  <span class="text-xs text-muted-foreground"> / {{ price.interval }}</span>
                  <span v-if="price.amount > 0" class="block text-xs text-muted-foreground">{{
                    $t('common.exclVat')
                  }}</span>
                </div>
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
          </div>
        </div>
      </div>
    </template>

    <p v-if="errorMessage" class="text-sm text-destructive">{{ errorMessage }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Loader2, ExternalLink, ShieldCheck, CreditCard, Check, Minus, Info } from 'lucide-vue-next'
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
import { Popover, PopoverContent, PopoverTrigger } from '@/platform/components/ui/popover'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import { useSubscriptionStore } from '@/platform/stores/subscription'
import { useConfirm } from '@/platform/composables/useConfirm'
import { useToast } from '@/platform/composables/useToast'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormatDate } from '@/platform/composables/useFormatDate'
import { useSaveFeedback } from '@/platform/composables/useSaveFeedback'
import type { SubscriptionOut, PlanOut, PlanPriceOut } from '@/platform/types'

const subscriptionStore = useSubscriptionStore()
const { t, tm, locale } = useI18n()
const { formatDate, formatDateTime } = useFormatDate()
const { toast } = useToast()
const { confirm } = useConfirm()
const { resolveError } = useErrorHandler()

const isLoading = ref(false)
const plansLoading = ref(false)
const isActing = ref(false)
const isPortalLoading = ref(false)
const checkoutId = ref<number | undefined>(undefined)
const isCheckingOut = ref(false)
const isTrialing = ref(false)
const trialId = ref<number | undefined>(undefined)
const switchId = ref<number | undefined>(undefined)
const { saving: emailSaving, saved: emailSaved, save: saveEmail } = useSaveFeedback()
const billingEmail = ref('')
const subscription = ref<SubscriptionOut | null>(null)
const availablePlans = ref<PlanOut[]>([])

const trialPrice = computed<PlanPriceOut | undefined>(() => {
  const last = availablePlans.value[availablePlans.value.length - 1]
  if (!last) return undefined
  for (const price of last.prices) {
    if (price.is_active && price.amount > 0 && price.trial_period_days) {
      return price
    }
  }
  return undefined
})

const paidPlans = computed(() =>
  availablePlans.value.filter((p) => p.prices.some((pr) => pr.is_active && pr.amount > 0)),
)
const errorMessage = ref('')

type ComparisonRow = {
  label: string
  stat?: boolean
  details?: string[]
  [planName: string]: string | boolean | string[] | undefined
}

const comparisonRows = computed(() => (tm('planComparisonRows') as ComparisonRow[]) ?? [])

async function loadSubscription() {
  isLoading.value = true
  try {
    const data = await subscriptionStore.getCurrentSubscription()
    subscription.value = data
    billingEmail.value = data.billing_email ?? ''
    subscriptionStore.subscriptionStatus = data.status
    subscriptionStore.subscriptionTrialEnd = data.trial_end
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status !== 404) {
      errorMessage.value = resolveError(err)
    }
  } finally {
    isLoading.value = false
  }
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') {
    loadSubscription()
  }
}

onMounted(async () => {
  await loadSubscription()

  plansLoading.value = true
  try {
    const data = await subscriptionStore.listPlans()
    availablePlans.value = data
      .filter((p) => p.is_active)
      .sort((a, b) => {
        const minPrice = (plan: typeof a) =>
          Math.min(...plan.prices.filter((p) => p.is_active).map((p) => p.amount), Infinity)
        return minPrice(a) - minPrice(b)
      })
  } catch {
    // Non-critical - plan list is optional context
  } finally {
    plansLoading.value = false
  }

  document.addEventListener('visibilitychange', onVisibilityChange)
})

onUnmounted(() => {
  document.removeEventListener('visibilitychange', onVisibilityChange)
})

function formatPrice(price: PlanPriceOut): string {
  const amount = price.amount / 100
  try {
    return new Intl.NumberFormat(locale.value, {
      style: 'currency',
      currency: price.currency,
    }).format(amount)
  } catch {
    return `${price.currency.toUpperCase()} ${amount.toFixed(2)}`
  }
}

function planName(price: PlanPriceOut | null): string {
  if (!price) return ''
  const plan = availablePlans.value.find((p) => p.prices.some((pr) => pr.id === price.id))
  return plan?.name ?? ''
}

function monthlyEquivalent(price: PlanPriceOut): number {
  const count = price.interval_count ?? 1
  return price.interval === 'year' ? price.amount / (12 * count) : price.amount / count
}

function statusBadgeVariant(
  status: string,
): 'success' | 'info' | 'warning' | 'secondary' | 'error' | 'outline' {
  const map: Record<string, 'success' | 'info' | 'warning' | 'secondary' | 'error'> = {
    active: 'success',
    trialing: 'info',
    past_due: 'warning',
    paused: 'warning',
    canceled: 'secondary',
    incomplete: 'error',
  }
  return map[status] ?? 'outline'
}

async function handleCancel() {
  const ok = await confirm(
    t('subscription.cancelTitle'),
    t('subscription.cancelDescription'),
    t('subscription.cancelConfirm'),
  )
  if (!ok) return
  isActing.value = true
  try {
    const data = await subscriptionStore.cancelSubscription()
    subscription.value = data
    toast({ title: t('subscription.cancelScheduledSuccess') })
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    isActing.value = false
  }
}

async function handleResume() {
  isActing.value = true
  try {
    const data = await subscriptionStore.resumeSubscription()
    subscription.value = data
    toast({ title: t('subscription.resumed') })
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    isActing.value = false
  }
}

async function handlePortal() {
  isPortalLoading.value = true
  try {
    const data = await subscriptionStore.getPortalUrl()
    const parsed = new URL(data.portal_url)
    if (!['https:', 'http:'].includes(parsed.protocol)) throw new Error('Invalid URL protocol')
    window.open(data.portal_url, '_blank', 'noopener,noreferrer')
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
  } finally {
    isPortalLoading.value = false
  }
}

async function handleSwitchPlan(priceId: number, priceAmount: number) {
  const currentAmount = subscription.value?.plan_price?.amount ?? 0
  const isUpgrade = priceAmount > currentAmount
  const isFreeToPaid = currentAmount === 0
  const ok = await confirm(
    t('subscription.switchPlanTitle'),
    t(
      isFreeToPaid
        ? 'subscription.switchPlanCheckoutDescription'
        : 'subscription.switchPlanDescription',
    ),
    t(isUpgrade ? 'subscription.upgrade' : 'subscription.downgrade'),
    isUpgrade ? 'default' : 'destructive',
  )
  if (!ok) return
  switchId.value = priceId
  try {
    const data = await subscriptionStore.switchPlan(priceId)
    if ('checkout_url' in data) {
      switchId.value = undefined
      window.location.href = data.checkout_url
    } else {
      subscription.value = data
      subscriptionStore.subscriptionStatus = data.status
      subscriptionStore.subscriptionTrialEnd = data.trial_end
      toast({ title: t('subscription.switchPlanSuccess') })
      switchId.value = undefined
    }
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
    switchId.value = undefined
  }
}

async function handleTrial(priceId: number) {
  trialId.value = priceId
  isTrialing.value = true
  try {
    const data = await subscriptionStore.startTrial(priceId)
    window.location.href = data.checkout_url
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
    trialId.value = undefined
    isTrialing.value = false
  }
}

async function handleSaveEmail() {
  try {
    const data = await saveEmail(() => subscriptionStore.updateBillingEmail(billingEmail.value))
    subscription.value = data
    billingEmail.value = data.billing_email ?? ''
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
  }
}

async function handleCheckout(priceId: number) {
  checkoutId.value = priceId
  isCheckingOut.value = true
  try {
    const data = await subscriptionStore.checkout(priceId)
    window.location.href = data.checkout_url
  } catch (err: unknown) {
    toast({ title: resolveError(err), variant: 'destructive' })
    checkoutId.value = undefined
    isCheckingOut.value = false
  }
}
</script>
