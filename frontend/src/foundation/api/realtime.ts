import { API_BASE_URL, getAccessToken } from './client'
import { readServerSentEvents, type ServerSentEvent } from '@/foundation/lib/sse'

/** The stream was refused for an expired or missing access token. */
export class EventStreamUnauthorizedError extends Error {}

export const realtimeApi = {
  /**
   * Opens the signed-in user's realtime event stream (`GET /v1/events`).
   * `fetch` rather than `EventSource`, which can't send the Authorization header.
   */
  async open(signal: AbortSignal): Promise<AsyncGenerator<ServerSentEvent>> {
    const token = getAccessToken()
    const response = await fetch(`${API_BASE_URL}/events`, {
      headers: {
        Accept: 'text/event-stream',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      cache: 'no-store',
      signal,
    })
    if (response.status === 401) throw new EventStreamUnauthorizedError()
    if (!response.ok || !response.body) {
      throw new Error(`Event stream failed with status ${response.status}`)
    }
    return readServerSentEvents(response.body)
  },
}
