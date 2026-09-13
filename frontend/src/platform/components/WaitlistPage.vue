<template>
  <div class="min-h-screen flex flex-col bg-slate-950 text-white">
    <!-- Top bar: logo + locale toggle -->
    <header class="container max-w-5xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
          <Radar class="w-4 h-4 text-slate-900" />
        </div>
        <span class="font-bold text-lg tracking-tight">{{ $t('app.name') }}</span>
      </div>
      <LocaleToggle />
    </header>

    <!-- Centered hero + form -->
    <main class="flex-1 flex items-center justify-center px-4 sm:px-6 py-12">
      <div class="w-full max-w-md text-center">
        <div
          class="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900 px-4 py-1.5 text-xs font-medium text-slate-300 mb-8"
        >
          <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          {{ $t('waitlist.badge') }}
        </div>

        <h1 class="text-3xl sm:text-4xl font-bold tracking-tight leading-tight">
          {{ $t('waitlist.headline') }}
        </h1>
        <p class="mt-4 text-slate-400 leading-relaxed">
          {{ $t('waitlist.sub') }}
        </p>

        <!-- Success state -->
        <div
          v-if="joined"
          class="mt-10 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-6 flex flex-col items-center gap-3"
        >
          <div class="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center">
            <CheckCircle2 class="w-5 h-5 text-emerald-400" />
          </div>
          <p class="text-sm text-emerald-100">{{ $t('waitlist.success') }}</p>
        </div>

        <!-- Form -->
        <form v-else class="mt-10 space-y-4 text-left" @submit.prevent="onSubmit">
          <div class="space-y-1.5">
            <label for="waitlist-name" class="text-sm font-medium text-slate-300">
              {{ $t('waitlist.nameLabel') }}
            </label>
            <input
              id="waitlist-name"
              v-model="name"
              type="text"
              :placeholder="$t('waitlist.namePlaceholder')"
              :disabled="isLoading"
              class="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-slate-400 focus:outline-none disabled:opacity-60"
            />
          </div>

          <div class="space-y-1.5">
            <label for="waitlist-email" class="text-sm font-medium text-slate-300">
              {{ $t('waitlist.emailLabel') }}
            </label>
            <input
              id="waitlist-email"
              v-model="form.email"
              type="text"
              :placeholder="$t('waitlist.emailPlaceholder')"
              :disabled="isLoading"
              class="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:border-slate-400 focus:outline-none disabled:opacity-60"
            />
            <p v-if="errors.email" class="text-xs text-red-400">{{ errors.email }}</p>
          </div>

          <p v-if="errorMessage" class="text-sm text-red-400">{{ errorMessage }}</p>

          <button
            type="submit"
            :disabled="isLoading"
            class="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-white px-7 py-3.5 text-sm font-semibold text-slate-900 hover:bg-slate-100 transition-colors disabled:opacity-60"
          >
            <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" />
            {{ $t('waitlist.submit') }}
          </button>
        </form>
      </div>
    </main>

    <footer
      class="container max-w-5xl mx-auto px-4 sm:px-6 py-6 text-center text-xs text-slate-600"
    >
      © {{ year }} {{ $t('app.name') }}
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Radar, CheckCircle2, Loader2 } from 'lucide-vue-next'
import { waitlistApi } from '@/platform/api/waitlist'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'

const { resolveError, resolveFieldErrors } = useErrorHandler()
const rules = useRules()
const { form, errors, validate } = useValidation({ email: rules.email })

const name = ref('')
const isLoading = ref(false)
const errorMessage = ref('')
const joined = ref(false)
const year = new Date().getFullYear()

async function onSubmit() {
  if (!validate()) return

  isLoading.value = true
  errorMessage.value = ''
  try {
    await waitlistApi.join({
      email: form.email,
      name: name.value.trim() || null,
    })
    joined.value = true
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    if (fieldErrors['body__email']) {
      errors.email = fieldErrors['body__email']
    } else {
      errorMessage.value = resolveError(err)
    }
  } finally {
    isLoading.value = false
  }
}
</script>
