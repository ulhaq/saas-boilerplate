import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'
import VueRouter from 'unplugin-vue-router/vite'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { VueRouterAutoImports } from 'unplugin-vue-router'
import { fileURLToPath, URL } from 'node:url'
import { BRAND } from './src/brand'
import { modulePackages } from './products.config.js'

/**
 * Fills the `%BRAND_NAME%` / `%MARKETING_ORIGIN%` placeholders in index.html,
 * so neither the domain nor the product name is hard-coded outside `src/brand.ts`.
 */
function brandAssets(): Plugin {
  return {
    name: 'brand-assets',
    transformIndexHtml(html) {
      return html
        .replace(/%BRAND_NAME%/g, BRAND.name)
        .replace(/%MARKETING_ORIGIN%/g, BRAND.marketingOrigin)
    },
  }
}

/**
 * Umami analytics (opt-in, compose profile `analytics`): adds the tracking
 * script to index.html only when VITE_UMAMI_SCRIPT_URL is set, so a setup
 * without Umami ships no dead script tag.
 */
function umamiScript(): Plugin {
  let env: Record<string, string> = {}
  return {
    name: 'umami-script',
    configResolved(config) {
      env = config.env
    },
    transformIndexHtml() {
      const src = env.VITE_UMAMI_SCRIPT_URL
      if (!src) return
      return [
        {
          tag: 'script',
          attrs: { defer: true, src, 'data-website-id': env.VITE_UMAMI_WEBSITE_ID ?? '' },
          injectTo: 'head',
        },
      ]
    },
  }
}

// The plugins regenerate these typing files for the editor; a test run must not.
const writeTypes = !process.env.VITEST

export default defineConfig({
  plugins: [
    brandAssets(),
    umamiScript(),
    VueRouter({
      routesFolder: ['src/foundation/pages', ...modulePackages.map((pkg) => `src/${pkg}/pages`)],
      dts: writeTypes && 'src/typed-router.d.ts',
    }),
    vue(),
    AutoImport({
      imports: [
        'vue',
        VueRouterAutoImports,
        { pinia: ['defineStore', 'storeToRefs'] },
        { '@vueuse/core': ['useDark', 'useToggle', 'useLocalStorage', 'useMediaQuery'] },
      ],
      dts: writeTypes && 'src/auto-imports.d.ts',
      vueTemplate: true,
    }),
    Components({
      dirs: ['src/foundation/components', ...modulePackages.map((pkg) => `src/${pkg}/components`)],
      dts: writeTypes && 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/v1': {
        target: process.env.API_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
      // Browser telemetry (VITE_FARO_URL=/collect) -> the Alloy agent's Faro receiver
      '/collect': {
        target: process.env.FARO_TARGET ?? 'http://localhost:12347',
        changeOrigin: true,
      },
    },
  },
})
