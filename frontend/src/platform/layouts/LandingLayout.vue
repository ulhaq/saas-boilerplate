<template>
  <div class="min-h-screen flex flex-col bg-white">
    <!-- Navbar -->
    <header class="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-slate-200">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6 flex items-center justify-between h-16">
        <!-- Logo -->
        <RouterLink
          :to="localePath('home')"
          class="flex items-center gap-2 shrink-0"
          @click.prevent="scrollToTop"
        >
          <div class="w-8 h-8 rounded-lg bg-slate-900 flex items-center justify-center">
            <Box class="w-4 h-4 text-white" />
          </div>
          <span class="font-bold text-slate-900 text-lg tracking-tight">{{ BRAND.name }}</span>
        </RouterLink>

        <!-- Centre nav links (desktop) -->
        <nav class="hidden md:flex items-center gap-6">
          <RouterLink
            v-for="link in navLinks"
            :key="link.to"
            :to="link.to"
            class="text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors"
          >
            {{ link.label }}
          </RouterLink>
        </nav>

        <!-- Right side (desktop) -->
        <!-- Language switching lives in the footer; the header keeps the CTA. -->
        <div class="hidden md:flex items-center gap-3">
          <Button
            as-child
            variant="ghost"
            class="px-3 text-slate-700 hover:text-slate-900 hover:bg-slate-100"
          >
            <RouterLink to="/login">
              {{ $t('landing.nav.login') }}
            </RouterLink>
          </Button>

          <RouterLink
            to="/register"
            class="inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 transition-colors"
          >
            {{ $t('landing.nav.cta') }}
          </RouterLink>
        </div>

        <!-- Mobile right: hamburger -->
        <div class="flex md:hidden items-center gap-2">
          <!--
            Icon-only, so it needs an explicit name: the icon is decorative and
            contributes nothing to the accessibility tree. `aria-expanded` and
            `aria-controls` tie it to the panel it opens.
          -->
          <button
            type="button"
            class="p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors"
            :aria-label="mobileOpen ? $t('common.closeMenu') : $t('common.openMenu')"
            :aria-expanded="mobileOpen"
            aria-controls="landing-mobile-menu"
            @click="mobileOpen = !mobileOpen"
          >
            <X v-if="mobileOpen" class="w-5 h-5" aria-hidden="true" />
            <Menu v-else class="w-5 h-5" aria-hidden="true" />
          </button>
        </div>
      </div>

      <!-- Mobile menu -->
      <div
        v-show="mobileOpen"
        id="landing-mobile-menu"
        class="md:hidden border-t border-slate-200 bg-white px-4 py-4 space-y-1"
      >
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="block px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
          @click="mobileOpen = false"
        >
          {{ link.label }}
        </RouterLink>
        <RouterLink
          to="/register"
          class="mt-1 inline-flex w-full items-center justify-center rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 transition-colors"
          @click="mobileOpen = false"
        >
          {{ $t('landing.nav.cta') }}
        </RouterLink>
        <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
          <RouterLink
            to="/login"
            class="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
            @click="mobileOpen = false"
          >
            {{ $t('landing.nav.login') }}
          </RouterLink>
          <LocaleToggle variant="slate" />
        </div>
      </div>
    </header>

    <!-- Page content -->
    <main class="flex-1">
      <slot />
    </main>

    <CookieBanner />

    <!-- Footer -->
    <footer class="border-t border-slate-200 bg-slate-50">
      <div class="container max-w-6xl mx-auto px-4 sm:px-6 py-12">
        <!--
          Four-column masthead. Every item belongs to a column with a defined
          edge, so nothing floats and adding a page later means adding a list
          item rather than rebalancing the layout. The hairline above each
          column matches the marketing pages' section treatment.
        -->
        <div class="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1fr_1fr] lg:gap-10">
          <!-- Masthead: what the product is. Legal identity sits on the legal pages. -->
          <div class="border-t border-slate-300 pt-4">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-md bg-slate-900 flex items-center justify-center">
                <Box class="w-3 h-3 text-white" />
              </div>
              <span class="text-sm font-semibold text-slate-900">{{ BRAND.name }}</span>
            </div>
            <p class="mt-4 max-w-xs text-xs text-slate-500 leading-relaxed">
              {{ $t('landing.footer.tagline') }}
            </p>
          </div>

          <!-- Produkt -->
          <div class="border-t border-slate-300 pt-4">
            <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {{ $t('landing.footer.product') }}
            </h2>
            <ul class="mt-4 space-y-2 text-xs text-slate-500">
              <li>
                <RouterLink
                  :to="localePath('features')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.nav.features') }}
                </RouterLink>
              </li>
              <li>
                <RouterLink
                  :to="localePath('pricing')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.nav.pricing') }}
                </RouterLink>
              </li>
              <li>
                <RouterLink to="/register" class="hover:text-slate-900 transition-colors">
                  {{ $t('landing.footer.register') }}
                </RouterLink>
              </li>
              <li>
                <RouterLink to="/login" class="hover:text-slate-900 transition-colors">
                  {{ $t('landing.nav.login') }}
                </RouterLink>
              </li>
              <li>
                <a
                  :href="API_DOCS_URL"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.footer.apiDocs') }}
                </a>
              </li>
            </ul>
          </div>

          <!-- Virksomhed -->
          <div class="border-t border-slate-300 pt-4">
            <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {{ $t('landing.footer.company') }}
            </h2>
            <ul class="mt-4 space-y-2 text-xs text-slate-500">
              <li>
                <RouterLink
                  :to="localePath('about')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.footer.about') }}
                </RouterLink>
              </li>
              <li>
                <RouterLink
                  :to="localePath('contact')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.footer.contact') }}
                </RouterLink>
              </li>
            </ul>
          </div>

          <!-- Juridisk -->
          <div class="border-t border-slate-300 pt-4">
            <h2 class="text-xs font-semibold uppercase tracking-wider text-slate-600">
              {{ $t('landing.footer.legal') }}
            </h2>
            <ul class="mt-4 space-y-2 text-xs text-slate-500">
              <li>
                <RouterLink
                  :to="localePath('privacy')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.footer.privacy') }}
                </RouterLink>
              </li>
              <li>
                <RouterLink
                  :to="localePath('terms')"
                  class="hover:text-slate-900 transition-colors"
                >
                  {{ $t('landing.footer.terms') }}
                </RouterLink>
              </li>
              <li>
                <button
                  type="button"
                  class="hover:text-slate-900 transition-colors"
                  @click="openSettings"
                >
                  {{ $t('cookie.settings') }}
                </button>
              </li>
            </ul>
          </div>
        </div>

        <!-- Fine print. Spacing only, no rule - the footer's top border is the
             page's single divider. -->
        <div
          class="mt-12 flex flex-col-reverse gap-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <!-- Company identity (name, address, registration number) lives on the legal pages. -->
          <p class="text-xs text-slate-600">
            {{ $t('landing.footer.copyright', { year: new Date().getFullYear() }) }}
          </p>
          <LocaleToggle variant="slate" />
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import { Box, Menu, X } from 'lucide-vue-next'
import { BRAND } from '@/brand'
import { Button } from '@/platform/components/ui/button'
import { useCookieConsent } from '@/platform/composables/useCookieConsent'
import { useTawkChat } from '@/platform/composables/useTawkChat'
import { useLocalePath } from '@/platform/composables/useLocalePath'
import { API_DOCS_URL } from '@/platform/constants'

const { t } = useI18n()
const { localePath } = useLocalePath()

const { openSettings } = useCookieConsent()
useTawkChat()

const mobileOpen = ref(false)

function scrollToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const navLinks = computed(() => [
  { to: localePath('home'), label: t('landing.nav.home') },
  { to: localePath('features'), label: t('landing.nav.features') },
  { to: localePath('pricing'), label: t('landing.nav.pricing') },
])
</script>
