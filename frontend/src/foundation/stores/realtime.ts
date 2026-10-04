import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { refreshAccessToken } from '@/foundation/api/client'
import { EventStreamUnauthorizedError, realtimeApi } from '@/foundation/api/realtime'

/**
 * A realtime event from the API (`backend/src/foundation/core/realtime.py`).
 * Events are hints that something changed - a handler re-fetches what it shows.
 */
export interface RealtimeEvent {
  type: string
  organization_id: number | null
  data: Record<string, unknown>
}

type EventHandler = (event: RealtimeEvent) => void
type SyncHandler = () => void

// Stream events the store handles itself.
const READY_EVENT = 'ready'
const RESYNC_EVENT = 'resync'

const RECONNECT_BASE_MS = 1_000
const RECONNECT_MAX_MS = 30_000
// A tab hidden this long closes its stream (browsers cap the connections open
// to one host); it reconnects, and re-syncs, when shown again.
const HIDDEN_DISCONNECT_MS = 5 * 60_000

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms)
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        resolve()
      },
      { once: true },
    )
  })
}

function backoff(attempt: number): number {
  const ms = Math.min(RECONNECT_BASE_MS * 2 ** attempt, RECONNECT_MAX_MS)
  return ms / 2 + Math.random() * (ms / 2)
}

function parseEvent(data: string): RealtimeEvent | null {
  try {
    return JSON.parse(data) as RealtimeEvent
  } catch {
    return null
  }
}

/**
 * The signed-in user's realtime event stream (`GET /v1/events`), kept open
 * while signed in: reconnects with backoff, refreshes an expired access token,
 * and pauses while the tab is hidden for long. Features subscribe with `on()`
 * for an event type and `onSync()` to re-fetch whenever they may have missed
 * events (each time the stream opens, and on `resync`).
 */
export const useRealtimeStore = defineStore('realtime', () => {
  const status = ref<'idle' | 'connecting' | 'open'>('idle')
  const isConnected = computed(() => status.value === 'open')

  const eventHandlers = new Map<string, Set<EventHandler>>()
  const syncHandlers = new Set<SyncHandler>()
  let controller: AbortController | null = null
  let wanted = false
  let hiddenTimer: ReturnType<typeof setTimeout> | null = null
  let watchingVisibility = false

  /** Run `handler` for every event of `type`; returns the unsubscribe function. */
  function on(type: string, handler: EventHandler): () => void {
    if (!eventHandlers.has(type)) eventHandlers.set(type, new Set())
    eventHandlers.get(type)!.add(handler)
    return () => eventHandlers.get(type)?.delete(handler)
  }

  /** Run `handler` whenever events may have been missed; returns the unsubscribe function. */
  function onSync(handler: SyncHandler): () => void {
    syncHandlers.add(handler)
    return () => syncHandlers.delete(handler)
  }

  function dispatch(event: RealtimeEvent): void {
    for (const handler of eventHandlers.get(event.type) ?? []) handler(event)
  }

  function sync(): void {
    for (const handler of syncHandlers) handler()
  }

  async function run(signal: AbortSignal): Promise<void> {
    let attempt = 0
    let refreshed = false
    while (!signal.aborted) {
      status.value = 'connecting'
      let opened = false
      try {
        for await (const message of await realtimeApi.open(signal)) {
          if (message.event === READY_EVENT) {
            opened = true
            status.value = 'open'
            sync()
            continue
          }
          const event = parseEvent(message.data)
          if (event?.type === RESYNC_EVENT) sync()
          else if (event) dispatch(event)
        }
      } catch (error) {
        if (signal.aborted) return
        if (error instanceof EventStreamUnauthorizedError && !refreshed) {
          try {
            await refreshAccessToken()
          } catch {
            // The session is over; the API client signs the user out on its next request.
            stopStream()
            return
          }
          refreshed = true
          continue
        }
      }
      if (opened) {
        // The server ends a stream after a while: reconnect with the current token.
        attempt = 0
        refreshed = false
        continue
      }
      await sleep(backoff(attempt++), signal)
      refreshed = false
    }
  }

  function startStream(): void {
    controller?.abort()
    const current = new AbortController()
    controller = current
    void run(current.signal).finally(() => {
      if (controller === current) status.value = 'idle'
    })
  }

  function stopStream(): void {
    controller?.abort()
    controller = null
    status.value = 'idle'
  }

  function onVisibilityChange(): void {
    if (hiddenTimer) clearTimeout(hiddenTimer)
    hiddenTimer = null
    if (!wanted) return
    if (document.hidden) {
      hiddenTimer = setTimeout(stopStream, HIDDEN_DISCONNECT_MS)
    } else if (!controller) {
      startStream()
    }
  }

  /** Open the stream - or reopen it, e.g. after switching organization (a new token). */
  function connect(): void {
    wanted = true
    if (!watchingVisibility) {
      document.addEventListener('visibilitychange', onVisibilityChange)
      watchingVisibility = true
    }
    startStream()
  }

  function disconnect(): void {
    wanted = false
    if (hiddenTimer) clearTimeout(hiddenTimer)
    hiddenTimer = null
    stopStream()
  }

  return { status, isConnected, on, onSync, connect, disconnect }
})
