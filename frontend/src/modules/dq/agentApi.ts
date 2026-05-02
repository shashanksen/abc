import { ApiError } from '@/lib/errors';
import { postStream, type StreamEvent } from '@/lib/agentStream';

export interface StreamCallbacks {
  /** Called once per `delta` event with the new chunk of text. */
  onDelta: (chunk: string) => void;
  /** Called when the orchestrator enters a tracked node. */
  onStep?: (info: { phase: string; node?: string }) => void;
  /** Called for tool invocations / responses (Phase 2 use). */
  onTool?: (info: { name: string; direction: 'request' | 'response'; summary?: string }) => void;
  /** Called once at stream start with the thread_id (use for refinement turns). */
  onThread?: (threadId: string) => void;
  /** Called once when the server finishes successfully. */
  onCompleted?: (info: { durationMs: number; fullText: string }) => void;
  /** Cancel mid-stream from the caller. */
  signal?: AbortSignal;
}

export interface BusinessRuleStreamRequest {
  description: string;
  /** Pass to continue a previous turn (refinement). Phase 2 UI only. */
  thread_id?: string;
}

class DqAgentApi {
  async streamBusinessRule(req: BusinessRuleStreamRequest, cb: StreamCallbacks): Promise<string> {
    let full = '';
    let resolved = false;

    return new Promise<string>(async (resolve, reject) => {
      try {
        await postStream(
          '/agent/dq/business-rule/stream',
          req,
          {
            signal: cb.signal,
            onEvent: (ev: StreamEvent) => {
              switch (ev.type) {
                case 'thread':
                  cb.onThread?.(ev.threadId);
                  break;
                case 'step':
                  cb.onStep?.({ phase: ev.phase, node: ev.node });
                  break;
                case 'tool':
                  cb.onTool?.({ name: ev.name, direction: ev.direction, summary: ev.summary });
                  break;
                case 'delta':
                  full += ev.text;
                  cb.onDelta(ev.text);
                  break;
                case 'completed':
                  resolved = true;
                  cb.onCompleted?.({ durationMs: ev.durationMs, fullText: full });
                  resolve(full);
                  break;
                case 'error':
                  resolved = true;
                  reject(new ApiError(502, { code: ev.code, message: ev.message }));
                  break;
              }
            },
          },
        );
        if (!resolved) {
          if (full) resolve(full);
          else reject(new ApiError(502, { code: 'CDP-AGT-0072', message: 'Empty agent response' }));
        }
      } catch (err) {
        if (!resolved) reject(err);
      }
    });
  }
}

export const dqAgentApi = new DqAgentApi();
