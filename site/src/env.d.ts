interface ImportMetaEnv {
  readonly PUBLIC_APP_URL?: string
  readonly PUBLIC_API_DOCS_URL?: string
  readonly PUBLIC_CTA_MODE?: 'signup' | 'waitlist'
  readonly PUBLIC_UMAMI_SCRIPT_URL?: string
  readonly PUBLIC_UMAMI_WEBSITE_ID?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
