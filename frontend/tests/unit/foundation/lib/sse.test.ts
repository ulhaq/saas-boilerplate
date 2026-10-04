import { describe, expect, test } from 'vitest'
import { readServerSentEvents } from '@/foundation/lib/sse'

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk))
      controller.close()
    },
  })
}

async function readAll(...chunks: string[]) {
  const events = []
  for await (const event of readServerSentEvents(streamOf(...chunks))) events.push(event)
  return events
}

describe('readServerSentEvents', () => {
  test('reads named and unnamed events', async () => {
    expect(await readAll('event: ready\ndata: {}\n\ndata: hello\n\n')).toEqual([
      { event: 'ready', data: '{}' },
      { event: 'message', data: 'hello' },
    ])
  })

  test('joins an event split across chunks, and its data lines', async () => {
    expect(await readAll('event: no', 'te\ndata: a\nda', 'ta: b\n', '\n')).toEqual([
      { event: 'note', data: 'a\nb' },
    ])
  })

  test('skips comments, other fields and an unfinished last event', async () => {
    expect(await readAll(': keep-alive\n\nid: 1\nretry: 5\ndata: x\r\n\r\ndata: cut off')).toEqual([
      { event: 'message', data: 'x' },
    ])
  })
})
