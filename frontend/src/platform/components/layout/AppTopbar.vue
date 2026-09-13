<template>
  <header class="h-16 border-b border-border bg-background flex items-center px-4 gap-4 shrink-0">
    <!-- Mobile menu button -->
    <button
      class="lg:hidden p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
      @click="uiStore.toggleSidebar()"
    >
      <Menu class="w-5 h-5" />
    </button>

    <!-- Breadcrumb -->
    <div class="flex items-center gap-1.5 text-sm flex-1">
      <span class="text-muted-foreground">{{ $t('nav.pages') }}</span>
      <ChevronRight class="w-3.5 h-3.5 text-muted-foreground/50" />
      <span class="font-medium text-foreground">{{ breadcrumb }}</span>
    </div>

    <!-- Right side -->
    <div class="flex items-center gap-2">
      <!-- Notifications -->
      <NotificationBell />

      <!-- User menu -->
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <button
            class="flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-accent transition-colors"
          >
            <div class="w-7 h-7 rounded-full bg-primary flex items-center justify-center">
              <span class="text-primary-foreground text-xs font-semibold">{{ userInitials }}</span>
            </div>
            <ChevronDown class="w-3.5 h-3.5 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" class="w-52">
          <DropdownMenuLabel>
            <p class="font-medium">{{ user?.name }}</p>
            <p class="text-xs text-muted-foreground font-normal">{{ user?.email }}</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuSub>
            <DropdownMenuSubTrigger class="cursor-pointer gap-2">
              <Globe class="w-4 h-4" />
              {{ $t('nav.language') }}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent class="w-32">
              <DropdownMenuItem
                v-for="lang in LOCALE_ORDER"
                :key="lang"
                class="cursor-pointer justify-between"
                @click="selectLocale(lang)"
              >
                {{ LOCALE_LABELS[lang] }}
                <Check v-if="locale === lang" class="w-3.5 h-3.5" />
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuSub>
            <DropdownMenuSubTrigger class="cursor-pointer gap-2">
              <Sun v-if="themeMode === 'light'" class="w-4 h-4" />
              <Moon v-else-if="themeMode === 'dark'" class="w-4 h-4" />
              <Monitor v-else class="w-4 h-4" />
              {{ $t('nav.theme.label') }}
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent class="w-32">
              <DropdownMenuItem class="cursor-pointer justify-between" @click="setTheme('light')">
                <span class="flex items-center gap-2">
                  <Sun class="w-4 h-4" />
                  {{ $t('nav.theme.light') }}
                </span>
                <Check v-if="themeMode === 'light'" class="w-3.5 h-3.5" />
              </DropdownMenuItem>
              <DropdownMenuItem class="cursor-pointer justify-between" @click="setTheme('dark')">
                <span class="flex items-center gap-2">
                  <Moon class="w-4 h-4" />
                  {{ $t('nav.theme.dark') }}
                </span>
                <Check v-if="themeMode === 'dark'" class="w-3.5 h-3.5" />
              </DropdownMenuItem>
              <DropdownMenuItem class="cursor-pointer justify-between" @click="setTheme('system')">
                <span class="flex items-center gap-2">
                  <Monitor class="w-4 h-4" />
                  {{ $t('nav.theme.system') }}
                </span>
                <Check v-if="themeMode === 'system'" class="w-3.5 h-3.5" />
              </DropdownMenuItem>
            </DropdownMenuSubContent>
          </DropdownMenuSub>
          <DropdownMenuItem as-child>
            <RouterLink to="/settings" class="cursor-pointer flex items-center gap-2">
              <Settings class="w-4 h-4" />
              {{ $t('nav.settings') }}
            </RouterLink>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            class="text-destructive cursor-pointer focus:text-destructive"
            @click="handleLogout"
          >
            <LogOut class="w-4 h-4 mr-2" />
            {{ $t('nav.logOut') }}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Menu,
  ChevronRight,
  ChevronDown,
  Sun,
  Moon,
  Monitor,
  Globe,
  Settings,
  LogOut,
  Check,
} from 'lucide-vue-next'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from '@/platform/components/ui/dropdown-menu'
import { LOCALE_ORDER, LOCALE_LABELS } from '@/plugins/i18n'
import type { SupportedLocale } from '@/plugins/i18n'
import { useAuthStore } from '@/platform/stores/auth'
import { useProfileStore } from '@/platform/stores/profile'
import { useUiStore } from '@/platform/stores/ui'

const authStore = useAuthStore()
const profileStore = useProfileStore()
const uiStore = useUiStore()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()
type ThemeMode = 'light' | 'dark' | 'system'
const themeMode = computed<ThemeMode>(() => (profileStore.user?.theme as ThemeMode) ?? 'system')

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

async function setTheme(mode: ThemeMode) {
  if (profileStore.user) profileStore.user.theme = mode
  applyTheme(mode)
  await profileStore.updateMe({ theme: mode })
}

async function selectLocale(lang: SupportedLocale) {
  locale.value = lang
  localStorage.setItem('locale', lang)
  await profileStore.updateMe({ locale: lang })
}

const user = computed(() => profileStore.user)
const breadcrumb = computed(() => {
  const key = route.meta.breadcrumb as string | undefined
  return key ? t(key) : ''
})

const userInitials = computed(() => {
  if (!user.value?.name) return '?'
  return user.value.name
    .split(' ')
    .map((n) => n[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
})

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>
