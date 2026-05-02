'use client';

import { useRef, useState } from 'react';
import { ApiError } from '@/lib/errors';

interface Props {
  /**
   * Called when the user clicks Generate. Receives the seed text, an
   * AbortSignal for cancellation, and a `setPhase` callback that the
   * parent should call from its `onStep` handler so the button can show
   * the current orchestration phase.
   */
  onGenerate: (
    seed: string,
    signal: AbortSignal,
    setPhase: (phase: string) => void,
  ) => Promise<string>;

  seed: string;
  minSeedLength?: number;
  label?: string;
  disabledHint?: string;

  /**
   * Show the orchestrator phase under the button while streaming. Default true.
   * Set false to hide all orchestration UI — the button reverts to a simple
   * "Generating…" state. Designed for the "minimal change to hide later" case.
   */
  showPhase?: boolean;
}

export function AIGenerateButton({
  onGenerate,
  seed,
  minSeedLength = 10,
  label = '✨ Generate with AI',
  disabledHint = 'Type at least a sentence before generating',
  showPhase = true,
}: Props) {
  const [streaming, setStreaming] = useState(false);
  const [phase,     setPhase]     = useState<string>('');
  const [error,     setError]     = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const seedReady = seed.trim().length >= minSeedLength;

  async function handleClick() {
    if (streaming) {
      abortRef.current?.abort();
      return;
    }
    setError(null);
    setPhase('');
    const controller = new AbortController();
    abortRef.current = controller;
    setStreaming(true);

    try {
      await onGenerate(seed, controller.signal, setPhase);
    } catch (e) {
      if (controller.signal.aborted) {
        // user-initiated stop — not an error
      } else if (e instanceof ApiError) {
        setError(e.userMessage());
      } else {
        setError('Generation failed. Please try again.');
      }
    } finally {
      setStreaming(false);
      setPhase('');
      abortRef.current = null;
    }
  }

  return (
    <div className="ai-generate">
      <button
        type="button"
        className={`btn btn-secondary btn-sm${streaming ? ' is-streaming' : ''}`}
        onClick={handleClick}
        disabled={!streaming && !seedReady}
        title={!seedReady ? disabledHint : undefined}
      >
        {streaming ? '◼ Stop' : label}
      </button>
      {streaming && showPhase && phase && (
        <span className="ai-generate-phase">{phase}…</span>
      )}
      {error && <span className="ai-generate-error">{error}</span>}
    </div>
  );
}
