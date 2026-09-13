<route lang="yaml">
meta:
  breadcrumb: settings.profile
</route>

<template>
  <div class="max-w-2xl">
    <PageHeader
      :title="$t('settings.profileInfo')"
      :description="$t('settings.profileInfoDescription')"
    />

    <Card class="mb-6">
      <CardContent class="pt-6">
        <form class="space-y-4" @submit.prevent="saveProfile">
          <div class="space-y-2">
            <Label>{{ $t('common.name') }}</Label>
            <Input v-model="profile.name" :disabled="savingProfile" />
            <p v-if="profileErrors.name" class="text-xs text-destructive">
              {{ profileErrors.name }}
            </p>
          </div>
          <div class="space-y-2">
            <Label>{{ $t('common.email') }}</Label>
            <Input v-model="profile.email" type="text" :disabled="savingProfile" />
            <p v-if="profileErrors.email" class="text-xs text-destructive">
              {{ profileErrors.email }}
            </p>
          </div>
          <p v-if="profileError" class="text-sm text-destructive">{{ profileError }}</p>
          <SaveButton
            :saving="savingProfile"
            :saved="profileSaved"
            :disabled="!profile.name.trim() || !profile.email.trim()"
          >
            {{ $t('common.saveChanges') }}
          </SaveButton>
        </form>
      </CardContent>
    </Card>

    <PageHeader
      :title="$t('settings.appearance')"
      :description="$t('settings.appearanceDescription')"
    />

    <div class="space-y-8">
      <!-- Language -->
      <div class="space-y-3">
        <Label>{{ $t('nav.language') }}</Label>
        <div class="grid grid-cols-2 gap-3">
          <button
            v-for="lang in LOCALE_ORDER"
            :key="lang"
            type="button"
            class="relative flex items-center gap-3 rounded-lg border-2 p-4 text-left transition-all"
            :class="
              locale === lang
                ? 'border-primary bg-primary/5'
                : 'border-border hover:border-muted-foreground/40'
            "
            @click="saveLocale(lang)"
          >
            <span class="text-sm font-medium">{{ LOCALE_LABELS[lang] }}</span>
            <Check
              v-if="locale === lang"
              :stroke-width="3"
              class="w-4 h-4 text-primary absolute right-3"
            />
          </button>
        </div>
      </div>

      <!-- Theme -->
      <div class="space-y-3">
        <Label>{{ $t('nav.theme.label') }}</Label>
        <div class="grid grid-cols-3 gap-3">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            type="button"
            class="relative flex flex-col rounded-lg border-2 overflow-hidden text-left transition-all"
            :class="
              themeMode === option.value
                ? 'border-primary'
                : 'border-border hover:border-muted-foreground/40'
            "
            @click="saveTheme(option.value)"
          >
            <!-- Preview -->
            <div class="w-full overflow-hidden pointer-events-none select-none">
              <!-- Light -->
              <svg
                v-if="option.value === 'light'"
                viewBox="0 0 200 120"
                xmlns="http://www.w3.org/2000/svg"
                class="w-full"
              >
                <rect width="200" height="120" fill="#f8fafc" />
                <rect width="36" height="120" fill="#f1f5f9" />
                <rect x="6" y="14" width="24" height="3.5" rx="1.5" fill="#cbd5e1" />
                <rect x="6" y="24" width="18" height="3" rx="1.5" fill="#e2e8f0" />
                <rect x="6" y="33" width="20" height="3" rx="1.5" fill="#e2e8f0" />
                <rect x="6" y="42" width="16" height="3" rx="1.5" fill="#e2e8f0" />
                <rect x="36" width="164" height="18" fill="#ffffff" />
                <rect x="36" y="18" width="164" height="0.75" fill="#e2e8f0" />
                <rect x="48" y="28" width="72" height="5" rx="2" fill="#e2e8f0" />
                <rect x="48" y="40" width="110" height="3.5" rx="1.5" fill="#f1f5f9" />
                <rect x="48" y="49" width="90" height="3.5" rx="1.5" fill="#f1f5f9" />
                <rect x="48" y="58" width="100" height="3.5" rx="1.5" fill="#f1f5f9" />
                <rect
                  x="48"
                  y="72"
                  width="120"
                  height="38"
                  rx="4"
                  fill="#ffffff"
                  stroke="#e2e8f0"
                  stroke-width="0.75"
                />
                <rect x="58" y="82" width="55" height="4" rx="1.5" fill="#e2e8f0" />
                <rect x="58" y="93" width="80" height="3" rx="1.5" fill="#f1f5f9" />
                <rect x="58" y="101" width="65" height="3" rx="1.5" fill="#f1f5f9" />
              </svg>

              <!-- Dark -->
              <svg
                v-else-if="option.value === 'dark'"
                viewBox="0 0 200 120"
                xmlns="http://www.w3.org/2000/svg"
                class="w-full"
              >
                <rect width="200" height="120" fill="#0f172a" />
                <rect width="36" height="120" fill="#1e293b" />
                <rect x="6" y="14" width="24" height="3.5" rx="1.5" fill="#475569" />
                <rect x="6" y="24" width="18" height="3" rx="1.5" fill="#334155" />
                <rect x="6" y="33" width="20" height="3" rx="1.5" fill="#334155" />
                <rect x="6" y="42" width="16" height="3" rx="1.5" fill="#334155" />
                <rect x="36" width="164" height="18" fill="#0f172a" />
                <rect x="36" y="18" width="164" height="0.75" fill="#1e293b" />
                <rect x="48" y="28" width="72" height="5" rx="2" fill="#334155" />
                <rect x="48" y="40" width="110" height="3.5" rx="1.5" fill="#1e293b" />
                <rect x="48" y="49" width="90" height="3.5" rx="1.5" fill="#1e293b" />
                <rect x="48" y="58" width="100" height="3.5" rx="1.5" fill="#1e293b" />
                <rect
                  x="48"
                  y="72"
                  width="120"
                  height="38"
                  rx="4"
                  fill="#1e293b"
                  stroke="#334155"
                  stroke-width="0.75"
                />
                <rect x="58" y="82" width="55" height="4" rx="1.5" fill="#334155" />
                <rect x="58" y="93" width="80" height="3" rx="1.5" fill="#0f172a" />
                <rect x="58" y="101" width="65" height="3" rx="1.5" fill="#0f172a" />
              </svg>

              <!-- System: left half light, right half dark -->
              <svg v-else viewBox="0 0 200 120" xmlns="http://www.w3.org/2000/svg" class="w-full">
                <!-- Light left half -->
                <rect width="100" height="120" fill="#f8fafc" />
                <rect width="36" height="120" fill="#f1f5f9" />
                <rect x="6" y="14" width="20" height="3.5" rx="1.5" fill="#cbd5e1" />
                <rect x="6" y="24" width="16" height="3" rx="1.5" fill="#e2e8f0" />
                <rect x="6" y="33" width="18" height="3" rx="1.5" fill="#e2e8f0" />
                <rect x="36" width="64" height="18" fill="#ffffff" />
                <rect x="36" y="18" width="64" height="0.75" fill="#e2e8f0" />
                <rect x="44" y="28" width="48" height="5" rx="2" fill="#e2e8f0" />
                <rect x="44" y="40" width="52" height="3.5" rx="1.5" fill="#f1f5f9" />
                <rect x="44" y="49" width="44" height="3.5" rx="1.5" fill="#f1f5f9" />
                <rect
                  x="44"
                  y="72"
                  width="52"
                  height="38"
                  rx="4"
                  fill="#ffffff"
                  stroke="#e2e8f0"
                  stroke-width="0.75"
                />
                <rect x="52" y="82" width="36" height="4" rx="1.5" fill="#e2e8f0" />
                <rect x="52" y="93" width="28" height="3" rx="1.5" fill="#f1f5f9" />
                <!-- Dark right half -->
                <rect x="100" width="100" height="120" fill="#0f172a" />
                <rect x="164" width="36" height="120" fill="#1e293b" />
                <rect x="169" y="14" width="20" height="3.5" rx="1.5" fill="#475569" />
                <rect x="169" y="24" width="16" height="3" rx="1.5" fill="#334155" />
                <rect x="169" y="33" width="18" height="3" rx="1.5" fill="#334155" />
                <rect x="100" width="64" height="18" fill="#0f172a" />
                <rect x="100" y="18" width="64" height="0.75" fill="#1e293b" />
                <rect x="108" y="28" width="48" height="5" rx="2" fill="#334155" />
                <rect x="108" y="40" width="52" height="3.5" rx="1.5" fill="#1e293b" />
                <rect x="108" y="49" width="44" height="3.5" rx="1.5" fill="#1e293b" />
                <rect
                  x="104"
                  y="72"
                  width="52"
                  height="38"
                  rx="4"
                  fill="#1e293b"
                  stroke="#334155"
                  stroke-width="0.75"
                />
                <rect x="112" y="82" width="36" height="4" rx="1.5" fill="#334155" />
                <rect x="112" y="93" width="28" height="3" rx="1.5" fill="#0f172a" />
                <!-- Divider -->
                <line
                  x1="100"
                  y1="0"
                  x2="100"
                  y2="120"
                  stroke="#94a3b8"
                  stroke-width="0.75"
                  stroke-dasharray="4 3"
                />
              </svg>
            </div>

            <!-- Label row -->
            <div class="flex items-center justify-between px-3 py-2.5 border-t border-border">
              <span class="text-sm font-medium">{{ option.label }}</span>
              <Check
                v-if="themeMode === option.value"
                :stroke-width="3"
                class="w-4 h-4 text-primary absolute right-3"
              />
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Sun, Moon, Monitor, Check } from 'lucide-vue-next'
import { Card, CardContent } from '@/platform/components/ui/card'
import { Input } from '@/platform/components/ui/input'
import { Label } from '@/platform/components/ui/label'
import PageHeader from '@/platform/components/common/PageHeader.vue'
import { useProfileStore } from '@/platform/stores/profile'
import { useErrorHandler } from '@/platform/composables/useErrorHandler'
import { useFormGuard } from '@/platform/composables/useFormGuard'
import { useSaveFeedback } from '@/platform/composables/useSaveFeedback'
import { LOCALE_ORDER, LOCALE_LABELS } from '@/plugins/i18n'
import type { SupportedLocale } from '@/plugins/i18n'

const profileStore = useProfileStore()
const { t, locale } = useI18n()
const { resolveError, resolveFieldErrors } = useErrorHandler()

type ThemeMode = 'light' | 'dark' | 'system'
const themeMode = computed<ThemeMode>(() => (profileStore.user?.theme as ThemeMode) ?? 'system')
const themeOptions = computed(() => [
  { value: 'light' as ThemeMode, label: t('nav.theme.light'), icon: Sun },
  { value: 'dark' as ThemeMode, label: t('nav.theme.dark'), icon: Moon },
  { value: 'system' as ThemeMode, label: t('nav.theme.system'), icon: Monitor },
])

function applyTheme(mode: ThemeMode) {
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  const dark = mode === 'dark' || (mode === 'system' && prefersDark)
  document.documentElement.classList.toggle('dark', dark)
}

const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
function onSystemChange() {
  if (themeMode.value === 'system') applyTheme('system')
}
mediaQuery.addEventListener('change', onSystemChange)
onUnmounted(() => mediaQuery.removeEventListener('change', onSystemChange))

async function saveTheme(mode: ThemeMode) {
  if (profileStore.user) profileStore.user.theme = mode
  applyTheme(mode)
  await profileStore.updateMe({ theme: mode })
}

async function saveLocale(lang: SupportedLocale) {
  locale.value = lang
  localStorage.setItem('locale', lang)
  await profileStore.updateMe({ locale: lang })
}

const profile = reactive({ name: '', email: '' })
const initial = reactive({ name: '', email: '' })
const profileErrors = reactive({ name: '', email: '' })
const profileError = ref('')
const { saving: savingProfile, saved: profileSaved, save: saveWithFeedback } = useSaveFeedback()

useFormGuard(() => profile.name !== initial.name || profile.email !== initial.email)

onMounted(() => {
  if (profileStore.user) {
    profile.name = profileStore.user.name
    profile.email = profileStore.user.email
    initial.name = profileStore.user.name
    initial.email = profileStore.user.email
  }
})

async function saveProfile() {
  profileErrors.name = profile.name.trim() ? '' : t('common.nameRequired')
  profileErrors.email = profile.email.trim() ? '' : t('common.emailRequired')
  if (profileErrors.name || profileErrors.email) return

  profileError.value = ''
  try {
    const data = await saveWithFeedback(() =>
      profileStore.updateMe({ name: profile.name, email: profile.email }),
    )
    profileStore.user = data
    initial.name = profile.name
    initial.email = profile.email
  } catch (err: unknown) {
    const fieldErrors = resolveFieldErrors(err)
    profileErrors.name = fieldErrors['body__name'] ?? ''
    profileErrors.email = fieldErrors['body__email'] ?? ''
    if (!profileErrors.name && !profileErrors.email) {
      profileError.value = resolveError(err)
    }
  }
}
</script>
