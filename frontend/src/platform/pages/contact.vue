<route lang="yaml">
meta:
  layout: landing
  requiresAuth: false
</route>

<template>
  <div class="bg-white">
    <div class="container max-w-6xl mx-auto px-4 sm:px-6 py-20">
      <div class="max-w-2xl">
        <h1 class="text-2xl sm:text-3xl font-semibold tracking-tight text-slate-900">
          {{ $t('landing.contact.title') }}
        </h1>
        <p class="mt-3 text-slate-500 leading-relaxed">
          {{ $t('landing.contact.sub') }}
        </p>
      </div>

      <!--
        Hairline columns, matching the section treatment on the landing and
        features pages rather than the rounded cards this page used before.
        The form is the primary column; the direct contact channel sits beside
        it for anyone who would rather use their own mail client.
      -->
      <div class="mt-10 grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_16rem] gap-x-12 gap-y-10">
        <div class="border-t border-slate-300 pt-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-600">
            {{ $t('landing.contact.formTitle') }}
          </h2>

          <div v-if="sent" class="mt-6 max-w-xl">
            <div class="flex items-center gap-2 text-slate-900">
              <CheckCircle2 class="w-5 h-5 text-emerald-600" aria-hidden="true" />
              <p class="text-sm font-medium">{{ $t('landing.contact.form.sentTitle') }}</p>
            </div>
            <p class="mt-2 text-sm text-slate-600 leading-relaxed">
              {{ $t('landing.contact.form.sentBody') }}
            </p>
          </div>

          <!--
            Plain slate-styled controls rather than the themed ui/ components:
            the landing layout is hard-coded light, so token colours that flip
            in dark mode would render white-on-white here.
          -->
          <form v-else class="mt-6 max-w-xl space-y-5" novalidate @submit.prevent="onSubmit">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-5">
              <div>
                <label :class="labelClass" for="contact-name">
                  {{ $t('landing.contact.form.name') }}
                </label>
                <input
                  id="contact-name"
                  v-model="form.name"
                  type="text"
                  autocomplete="name"
                  :class="fieldClass(!!errors.name)"
                  :placeholder="$t('landing.contact.form.namePlaceholder')"
                  :disabled="isLoading"
                  :aria-invalid="!!errors.name"
                  :aria-describedby="errors.name ? 'contact-name-error' : undefined"
                />
                <p v-if="errors.name" id="contact-name-error" :class="errorClass">
                  {{ errors.name }}
                </p>
              </div>

              <div>
                <label :class="labelClass" for="contact-email">
                  {{ $t('landing.contact.form.email') }}
                </label>
                <input
                  id="contact-email"
                  v-model="form.email"
                  type="text"
                  autocomplete="email"
                  :class="fieldClass(!!errors.email)"
                  :placeholder="$t('landing.contact.form.emailPlaceholder')"
                  :disabled="isLoading"
                  :aria-invalid="!!errors.email"
                  :aria-describedby="errors.email ? 'contact-email-error' : undefined"
                />
                <p v-if="errors.email" id="contact-email-error" :class="errorClass">
                  {{ errors.email }}
                </p>
              </div>
            </div>

            <div>
              <label :class="labelClass" for="contact-subject">
                {{ $t('landing.contact.form.subject') }}
              </label>
              <input
                id="contact-subject"
                v-model="form.subject"
                type="text"
                :class="fieldClass(!!errors.subject)"
                :placeholder="$t('landing.contact.form.subjectPlaceholder')"
                :disabled="isLoading"
                :aria-invalid="!!errors.subject"
                :aria-describedby="errors.subject ? 'contact-subject-error' : undefined"
              />
              <p v-if="errors.subject" id="contact-subject-error" :class="errorClass">
                {{ errors.subject }}
              </p>
            </div>

            <div>
              <label :class="labelClass" for="contact-message">
                {{ $t('landing.contact.form.message') }}
              </label>
              <textarea
                id="contact-message"
                v-model="form.message"
                rows="6"
                :class="[fieldClass(!!errors.message), 'resize-y']"
                :placeholder="$t('landing.contact.form.messagePlaceholder')"
                :disabled="isLoading"
                :aria-invalid="!!errors.message"
                :aria-describedby="errors.message ? 'contact-message-error' : undefined"
              />
              <p v-if="errors.message" id="contact-message-error" :class="errorClass">
                {{ errors.message }}
              </p>
            </div>

            <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>

            <!-- Same treatment as the header/footer CTA. -->
            <button
              type="submit"
              class="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 transition-colors disabled:opacity-60 disabled:hover:bg-slate-900"
              :disabled="isLoading"
            >
              <Loader2 v-if="isLoading" class="w-4 h-4 animate-spin" aria-hidden="true" />
              {{ $t('landing.contact.form.submit') }}
            </button>
          </form>
        </div>

        <!-- Contact channel only - legal identity lives on the legal pages. -->
        <div class="border-t border-slate-300 pt-4">
          <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-600">
            {{ $t('landing.contact.contactTitle') }}
          </h2>
          <p class="mt-4 text-xs text-slate-600">{{ $t('landing.contact.email') }}</p>
          <a
            :href="`mailto:${BRAND.supportEmail}`"
            class="mt-1 inline-block text-sm font-medium text-slate-900 hover:underline underline-offset-2"
          >
            {{ BRAND.supportEmail }}
          </a>
          <p class="mt-3 text-xs text-slate-600 leading-relaxed">
            {{ $t('landing.contact.responseTime') }}
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { BRAND } from '@/brand'
import { CheckCircle2, Loader2 } from 'lucide-vue-next'
import { useContactStore } from '@/platform/stores/contact'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useValidation } from '@/platform/composables/useValidation'
import { useRules } from '@/platform/composables/useRules'
import type { Rule } from '@/platform/composables/useRules'

const { t, locale } = useI18n()
const { resolveError, resolveFieldErrors } = useErrorHandler()
const rules = useRules()
const contactStore = useContactStore()

const labelClass = 'block text-xs font-medium text-slate-700'
const errorClass = 'mt-1.5 text-xs text-red-600'

function fieldClass(invalid: boolean): string {
  return [
    'mt-2 block w-full rounded-lg border bg-white px-3 py-2 text-sm text-slate-900',
    'placeholder:text-slate-400 transition-colors focus:outline-none focus:ring-1',
    'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
    invalid
      ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
      : 'border-slate-300 focus:border-slate-900 focus:ring-slate-900',
  ].join(' ')
}

// Mirrors the min_length on ContactMessageIn.message so a too-short message is
// caught before it costs a round trip.
const MESSAGE_MIN_LENGTH = 10

const messageRules: Rule[] = [
  (v) => !!v.trim() || t('common.required'),
  (v) => v.trim().length >= MESSAGE_MIN_LENGTH || t('landing.contact.form.messageTooShort'),
]

const { form, errors, validate } = useValidation({
  name: rules.required,
  email: rules.email,
  subject: rules.required,
  message: messageRules,
})

const isLoading = ref(false)
const errorMessage = ref('')
const sent = ref(false)

async function onSubmit() {
  if (!validate()) return

  isLoading.value = true
  errorMessage.value = ''
  try {
    await contactStore.submit({
      name: form.name,
      email: form.email,
      subject: form.subject,
      message: form.message,
      locale: locale.value,
    })
    sent.value = true
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    let matched = false
    for (const field of ['name', 'email', 'subject', 'message'] as const) {
      const fieldError = fieldErrors[`body__${field}`]
      if (fieldError) {
        errors[field] = fieldError
        matched = true
      }
    }
    if (!matched) errorMessage.value = resolveError(err)
  } finally {
    isLoading.value = false
  }
}
</script>
