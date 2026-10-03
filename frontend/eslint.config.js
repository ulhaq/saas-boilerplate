import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import tsParser from '@typescript-eslint/parser'
import tsPlugin from '@typescript-eslint/eslint-plugin'
import vueParser from 'vue-eslint-parser'
import prettier from 'eslint-config-prettier'
import globals from 'globals'
import { modulePackages, productPackages } from './products.config.js'

const autoImportedGlobals = {
  EffectScope: 'readonly',
  computed: 'readonly',
  createApp: 'readonly',
  customRef: 'readonly',
  defineAsyncComponent: 'readonly',
  defineComponent: 'readonly',
  defineStore: 'readonly',
  effectScope: 'readonly',
  getCurrentInstance: 'readonly',
  getCurrentScope: 'readonly',
  h: 'readonly',
  inject: 'readonly',
  isProxy: 'readonly',
  isReactive: 'readonly',
  isReadonly: 'readonly',
  isRef: 'readonly',
  markRaw: 'readonly',
  nextTick: 'readonly',
  onActivated: 'readonly',
  onBeforeMount: 'readonly',
  onBeforeRouteLeave: 'readonly',
  onBeforeRouteUpdate: 'readonly',
  onBeforeUnmount: 'readonly',
  onBeforeUpdate: 'readonly',
  onDeactivated: 'readonly',
  onErrorCaptured: 'readonly',
  onMounted: 'readonly',
  onRenderTracked: 'readonly',
  onRenderTriggered: 'readonly',
  onScopeDispose: 'readonly',
  onServerPrefetch: 'readonly',
  onUnmounted: 'readonly',
  onUpdated: 'readonly',
  onWatcherCleanup: 'readonly',
  provide: 'readonly',
  reactive: 'readonly',
  readonly: 'readonly',
  ref: 'readonly',
  resolveComponent: 'readonly',
  shallowReactive: 'readonly',
  shallowReadonly: 'readonly',
  shallowRef: 'readonly',
  storeToRefs: 'readonly',
  toRaw: 'readonly',
  toRef: 'readonly',
  toRefs: 'readonly',
  toValue: 'readonly',
  triggerRef: 'readonly',
  unref: 'readonly',
  useAttrs: 'readonly',
  useCssModule: 'readonly',
  useCssVars: 'readonly',
  useDark: 'readonly',
  useId: 'readonly',
  useLocalStorage: 'readonly',
  useMediaQuery: 'readonly',
  useModel: 'readonly',
  useRoute: 'readonly',
  useRouter: 'readonly',
  useSlots: 'readonly',
  useTemplateRef: 'readonly',
  useToggle: 'readonly',
  watch: 'readonly',
  watchEffect: 'readonly',
  watchPostEffect: 'readonly',
  watchSyncEffect: 'readonly',
}

export default [
  js.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  prettier,
  {
    files: ['**/*.{ts,tsx,vue}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...autoImportedGlobals,
      },
    },
  },
  {
    files: ['playwright.config.ts', 'tests/**/*.ts', 'vite.config.ts', 'scripts/**/*.mjs'],
    languageOptions: {
      globals: {
        ...globals.node,
        ...globals.browser,
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      parser: tsParser,
      globals: {
        ...globals.browser,
        ...autoImportedGlobals,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
      },
      globals: {
        ...globals.browser,
        ...autoImportedGlobals,
      },
    },
    plugins: {
      '@typescript-eslint': tsPlugin,
    },
    rules: {
      ...tsPlugin.configs.recommended.rules,
      'vue/multi-word-component-names': 'off',
      'vue/require-default-prop': 'off',
      '@typescript-eslint/no-unused-vars': [
        'error',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
    },
  },
  {
    // Boundary contract (mirrors backend import-linter): the foundation shell
    // must never import from billing or the product domain.
    files: ['src/foundation/**/*.{ts,tsx,vue}', 'tests/unit/foundation/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            ...modulePackages.map((pkg) => ({
              group: [`@/${pkg}`, `@/${pkg}/**`, `**/${pkg}/**`],
              message: `Foundation code must not import from a module (src/${pkg}).`,
            })),
            {
              group: ['@/products'],
              message: 'Foundation code must not import the product list (src/products.ts).',
            },
          ],
        },
      ],
    },
  },
  {
    // Billing is an optional foundation module: products may build on it, but it
    // never depends on a product.
    files: ['src/billing/**/*.{ts,tsx,vue}', 'tests/unit/billing/**/*.ts'],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          patterns: [
            ...productPackages.map((pkg) => ({
              group: [`@/${pkg}`, `@/${pkg}/**`, `**/${pkg}/**`],
              message: `Billing must not import from the product domain (src/${pkg}).`,
            })),
            {
              group: ['@/products'],
              message: 'Billing must not import the module list (src/products.ts).',
            },
          ],
        },
      ],
    },
  },
  {
    ignores: [
      'dist/',
      'node_modules/',
      'playwright-report/',
      'test-results/',
      'src/auto-imports.d.ts',
      'src/components.d.ts',
      'src/typed-router.d.ts',
    ],
  },
]
