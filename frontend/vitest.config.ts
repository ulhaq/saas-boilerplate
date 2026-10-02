import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

// Component tests: `src/**/*.test.ts`, run in a simulated DOM. End-to-end
// tests are Playwright's (`tests/e2e`, `npm run test:e2e`).
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'happy-dom',
      include: ['src/**/*.test.ts'],
    },
  }),
)
