import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config.ts'

// Component tests: `tests/unit/**/*.test.ts` (mirroring `src/`), run in a
// simulated DOM. End-to-end tests are Playwright's (`tests/e2e`,
// `npm run test:e2e`).
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'happy-dom',
      include: ['tests/unit/**/*.test.ts'],
    },
  }),
)
