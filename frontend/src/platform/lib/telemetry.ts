import type { App } from 'vue'
import type { TransportItem } from '@grafana/faro-web-sdk'

// Query/fragment parameters that carry secrets in this app's URLs
// (/invite?token=, /reset-password?token=, /verify-email?token=, OAuth codes).
const SENSITIVE_PARAM = /([?&#](?:token|code|key|secret|password)=)[^&#"\s\\]*/gi

/** Redact secret-bearing URL parameters anywhere in a telemetry item (page
 * URL, error messages, stack traces, ...). Items are plain JSON data. */
export function scrubUrls<T>(item: T): T {
  return JSON.parse(JSON.stringify(item).replace(SENSITIVE_PARAM, '$1<redacted>')) as T
}

/**
 * Browser telemetry via Grafana Faro: uncaught errors, Vue errors and web
 * vitals, sent to the Alloy agent's Faro receiver (see observability/README.md).
 *
 * Off unless VITE_FARO_URL is set, and loaded lazily so the SDK stays out of
 * the main bundle. Session tracking is disabled, so nothing is stored on the
 * visitor's device and no cookie consent is needed; no user identity is sent.
 */
export async function initTelemetry(app: App): Promise<void> {
  const url = import.meta.env.VITE_FARO_URL as string | undefined
  if (!url) return

  const { initializeFaro, getWebInstrumentations } = await import('@grafana/faro-web-sdk')
  const faro = initializeFaro({
    url,
    app: { name: 'frontend', environment: import.meta.env.MODE },
    // console.error capture would duplicate the Vue errors reported below
    instrumentations: getWebInstrumentations({ captureConsole: false }),
    sessionTracking: { enabled: false },
    beforeSend: (item: TransportItem) => scrubUrls(item),
  })

  const previous = app.config.errorHandler
  app.config.errorHandler = (err, instance, info) => {
    faro.api.pushError(err instanceof Error ? err : new Error(String(err)), {
      context: { vueInfo: info },
    })
    if (previous) previous(err, instance, info)
    else console.error(err)
  }
}
