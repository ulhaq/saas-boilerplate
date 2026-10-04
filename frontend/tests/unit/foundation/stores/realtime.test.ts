import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { refreshAccessToken } from '@/foundation/api/client'
import { EventStreamUnauthorizedError, realtimeApi } from '@/foundation/api/realtime'
import type { ServerSentEvent } from '@/foundation/lib/sse'
import { useRealtimeStore } from '@/foundation/stores/realtime'

vi.mock('@/foundation/api/realtime', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/foundation/api/realtime')>()),
  realtimeApi: { open: vi.fn() },
}))
vi.mock('@/foundation/api/client', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/foundation/api/client')>()),
  refreshAccessToken: vi.fn(),
}))

const open = vi.mocked(realtimeApi.open)

/** A stream that yields `messages`, then stays open until aborted. */
function streamOf(messages: ServerSentEvent[], signal: AbortSignal) {
  return (async function* () {
    yield* messages
    await new Promise((resolve) => signal.addEventListener('abort', resolve))
  })()
}

const event = (type: string, data: Record<string, unknown> = {}): ServerSentEvent => ({
  event: type,
  data: JSON.stringify({ type, organization_id: 1, data }),
})
const READY: ServerSentEvent = { event: 'ready', data: '{}' }

let store: ReturnType<typeof useRealtimeStore>

beforeEach(() => {
  setActivePinia(createPinia())
  store = useRealtimeStore()
  open.mockReset()
  vi.mocked(refreshAccessToken).mockReset()
})

afterEach(() => store.disconnect())

describe('realtime store', () => {
  test('syncs when the stream opens and hands events to their handlers', async () => {
    open.mockImplementation(async (signal) =>
      streamOf([READY, event('thing.changed', { id: 7 }), event('other')], signal),
    )
    const sync = vi.fn()
    const changed = vi.fn()
    store.onSync(sync)
    store.on('thing.changed', changed)

    store.connect()

    await vi.waitFor(() => expect(changed).toHaveBeenCalledTimes(1))
    expect(store.isConnected).toBe(true)
    expect(sync).toHaveBeenCalledTimes(1)
    expect(changed.mock.calls[0][0].data).toEqual({ id: 7 })
  })

  test('a resync event re-runs the sync handlers', async () => {
    open.mockImplementation(async (signal) => streamOf([READY, event('resync')], signal))
    const sync = vi.fn()
    store.onSync(sync)

    store.connect()

    await vi.waitFor(() => expect(sync).toHaveBeenCalledTimes(2))
  })

  test('refreshes an expired token and reconnects', async () => {
    open
      .mockRejectedValueOnce(new EventStreamUnauthorizedError())
      .mockImplementation(async (signal) => streamOf([READY], signal))
    vi.mocked(refreshAccessToken).mockResolvedValue('new-token')

    store.connect()

    await vi.waitFor(() => expect(store.isConnected).toBe(true))
    expect(refreshAccessToken).toHaveBeenCalledTimes(1)
    expect(open).toHaveBeenCalledTimes(2)
  })

  test('stops when the session cannot be refreshed', async () => {
    open.mockRejectedValue(new EventStreamUnauthorizedError())
    vi.mocked(refreshAccessToken).mockRejectedValue(new Error('signed out'))

    store.connect()

    await vi.waitFor(() => expect(refreshAccessToken).toHaveBeenCalled())
    await vi.waitFor(() => expect(store.status).toBe('idle'))
    expect(open).toHaveBeenCalledTimes(1)
  })

  test('reconnects at once when the server ends an open stream', async () => {
    open
      .mockImplementationOnce(async () =>
        (async function* () {
          yield READY
        })(),
      )
      .mockImplementation(async (signal) => streamOf([READY], signal))
    const sync = vi.fn()
    store.onSync(sync)

    store.connect()

    await vi.waitFor(() => expect(sync).toHaveBeenCalledTimes(2))
    expect(open).toHaveBeenCalledTimes(2)
  })

  test('an unsubscribed handler gets no more events, and disconnect closes the stream', async () => {
    let signal: AbortSignal | undefined
    open.mockImplementation(async (s) => {
      signal = s
      return streamOf([READY, event('thing.changed')], s)
    })
    const changed = vi.fn()
    store.on('thing.changed', changed)()

    store.connect()
    await vi.waitFor(() => expect(store.isConnected).toBe(true))
    store.disconnect()

    expect(changed).not.toHaveBeenCalled()
    expect(signal?.aborted).toBe(true)
    expect(store.status).toBe('idle')
  })
})
