/**
 * Streaming helper for agent endpoints.
 *
 * Handles the full Phase-1-with-orchestrator event vocabulary:
 *   - thread     — emitted once at start; carries the thread_id for refinement turns
 *   - step       — orchestrator entered a node ("Drafting rule")
 *   - tool       — a tool was invoked or returned (Phase 2 use)
 *   - delta      — incremental text from the LLM
 *   - completed  — stream finished successfully
 *   - error      — stream failed
 *
 * Why fetch + ReadableStream instead of EventSource:
 *   EventSource doesn't support custom headers — we can't send
 *   `Authorization: Bearer <jwt>` with it. fetch + manual SSE parser works
 *   with the existing JWT-in-header auth.
 */
import { TokenStorage } from './tokenStorage';
import { ApiError } from './errors';

export type StreamEvent =
  | { type: 'thread';    threadId: string }
  | { type: 'step';      phase: string; node?: string }
  | { type: 'tool';      name: string; direction: 'request' | 'response'; summary?: string }
  | { type: 'delta';     text: string }
  | { type: 'completed'; durationMs: number }
  | { type: 'error';     code: string; message: string };

export interface StreamOptions {
  onEvent: (ev: StreamEvent) => void;
  signal?: AbortSignal;
}

export async function postStream(
  path: string,
  body: unknown,
  opts: StreamOptions,
): Promise<void> {
  const url = path.startsWith('/') ? `/api${path}` : `/api/${path}`;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };
  const token = TokenStorage.get();
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    signal: opts.signal,
    cache: 'no-store',
  });

  if (!res.ok) {
    const text = await res.text();
    let parsed: unknown = null;
    try { parsed = text ? JSON.parse(text) : null; } catch { parsed = text; }
    const errPayload =
      (parsed as { error?: { code: string; message: string; detail?: string | null } })?.error
      ?? { code: 'CDP-SYS-0091', message: 'Unknown error', detail: text };
    throw new ApiError(res.status, errPayload);
  }
  if (!res.body) {
    throw new ApiError(500, { code: 'CDP-SYS-0091', message: 'No response body' });
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    let sepIdx: number;
    while ((sepIdx = findEventBoundary(buffer)) !== -1) {
      const rawEvent = buffer.slice(0, sepIdx);
      buffer = buffer.slice(sepIdx).replace(/^(\r?\n){1,2}/, '');

      const dispatched = parseAndDispatch(rawEvent, opts.onEvent);
      if (dispatched === 'error') {
        try { await reader.cancel(); } catch { /* ignore */ }
        return;
      }
    }
  }

  if (buffer.trim().length > 0) {
    parseAndDispatch(buffer, opts.onEvent);
  }
}

function findEventBoundary(buf: string): number {
  const a = buf.indexOf('\n\n');
  const b = buf.indexOf('\r\n\r\n');
  if (a === -1) return b === -1 ? -1 : b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function parseAndDispatch(
  rawEvent: string,
  onEvent: (ev: StreamEvent) => void,
): 'ok' | 'error' {
  let eventName: string | null = null;
  const dataLines: string[] = [];

  for (const line of rawEvent.split(/\r?\n/)) {
    if (line.startsWith(':')) continue;
    if (line.startsWith('event:')) eventName = line.slice('event:'.length).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice('data:'.length).replace(/^ /, ''));
  }
  if (!eventName || dataLines.length === 0) return 'ok';

  let payload: Record<string, unknown>;
  try {
    payload = JSON.parse(dataLines.join('\n'));
  } catch {
    return 'ok';
  }

  switch (eventName) {
    case 'thread':
      onEvent({ type: 'thread', threadId: String(payload.thread_id ?? '') });
      return 'ok';
    case 'step':
      onEvent({
        type: 'step',
        phase: String(payload.phase ?? ''),
        node: payload.node ? String(payload.node) : undefined,
      });
      return 'ok';
    case 'tool':
      onEvent({
        type: 'tool',
        name: String(payload.name ?? ''),
        direction: (payload.direction === 'response' ? 'response' : 'request'),
        summary: payload.summary ? String(payload.summary) : undefined,
      });
      return 'ok';
    case 'delta':
      onEvent({ type: 'delta', text: String(payload.text ?? '') });
      return 'ok';
    case 'completed':
      onEvent({ type: 'completed', durationMs: Number(payload.duration_ms ?? 0) });
      return 'ok';
    case 'error':
      onEvent({
        type: 'error',
        code: String(payload.code ?? 'CDP-SYS-0091'),
        message: String(payload.message ?? 'Unknown error'),
      });
      return 'error';
    default:
      return 'ok';
  }
}
