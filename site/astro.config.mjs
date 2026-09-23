// @ts-check
import { existsSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'astro/config'
import { loadEnv } from 'vite'
import sitemap from '@astrojs/sitemap'

const env = loadEnv(process.env.NODE_ENV ?? 'development', process.cwd(), '')

// Build-time theme switch: `@theme` resolves to src/themes/<SITE_THEME>/, so
// only the chosen theme's CSS, fonts and hero visual end up in the build.
const themesDir = fileURLToPath(new URL('./src/themes/', import.meta.url))
const themes = readdirSync(themesDir, { withFileTypes: true })
  .filter((entry) => entry.isDirectory() && existsSync(`${themesDir}${entry.name}/config.ts`))
  .map((entry) => entry.name)
const theme = env.SITE_THEME || 'editorial'
if (!themes.includes(theme)) {
  throw new Error(`SITE_THEME="${theme}" is not a theme. Choose one of: ${themes.join(', ')}`)
}

export default defineConfig({
  // Canonical origin of the site: canonical/hreflang tags, OG image, sitemap.
  site: env.SITE_URL || 'https://example.com',
  build: { format: 'directory' },
  integrations: [
    sitemap({ filter: (page) => !page.endsWith('/404/') && new URL(page).pathname !== '/' }),
  ],
  server: { port: 4321, host: true },
  vite: {
    resolve: { alias: { '@theme': `${themesDir}${theme}` } },
    server: {
      // Same-origin API in dev, as nginx does in production (nginx.conf.template).
      proxy: { '/v1': { target: env.API_TARGET || 'http://localhost:8000', changeOrigin: true } },
    },
  },
})
