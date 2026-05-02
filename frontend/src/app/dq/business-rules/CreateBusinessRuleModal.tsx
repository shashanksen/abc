'use client';

/**
 * Phase 1 with orchestrator: this modal now wires the new event types.
 * Differences from simple Phase 1:
 *   - `onStep` callback updates the AIGenerateButton's phase indicator
 *   - `onThread` captures the thread_id (stored in state for Phase 2 refinement)
 */
import { useEffect, useState } from 'react';
import { dqApi, type Dimension } from '@/modules/dq/api';
import { dqAgentApi } from '@/modules/dq/agentApi';
import { AIGenerateButton } from '@/components/dq/AIGenerateButton';
import { ApiError } from '@/lib/errors';

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function CreateBusinessRuleModal({ open, onClose, onCreated }: Props) {
  const [code,        setCode]        = useState('');
  const [dimensionId, setDimensionId] = useState<string>('');
  const [edeMapping,  setEdeMapping]  = useState('');
  const [seed,        setSeed]        = useState('');
  const [ruleText,    setRuleText]    = useState('');
  const [streaming,   setStreaming]   = useState(false);
  const [submitting,  setSubmitting]  = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [dimensions,  setDimensions]  = useState<Dimension[]>([]);
  // Phase 1 stores the thread_id but doesn't use it. Phase 2 will hook a
  // "Refine with feedback" button that sends the next prompt with this id.
  const [threadId,    setThreadId]    = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    dqApi.listDimensions().then(setDimensions).catch(() => setDimensions([]));
  }, [open]);

  useEffect(() => {
    if (!open) {
      setCode(''); setDimensionId(''); setEdeMapping('');
      setSeed(''); setRuleText('');
      setStreaming(false); setSubmitError(null);
      setThreadId(null);
    }
  }, [open]);

  async function handleGenerate(
    seedText: string,
    signal: AbortSignal,
    setPhase: (phase: string) => void,
  ): Promise<string> {
    setRuleText('');
    setStreaming(true);
    try {
      return await dqAgentApi.streamBusinessRule(
        { description: seedText, thread_id: threadId ?? undefined },
        {
          signal,
          onDelta: (chunk) => setRuleText((prev) => prev + chunk),
          onStep:  ({ phase }) => setPhase(phase),
          onThread: (id) => setThreadId(id),
        },
      );
    } finally {
      setStreaming(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      await dqApi.createBusinessRule({
        code: code.trim(),
        dimension_id: dimensionId || undefined,
        ede_mapping: edeMapping.trim() || undefined,
        rule_text: ruleText.trim(),
      });
      onCreated();
      onClose();
    } catch (e) {
      setSubmitError(e instanceof ApiError ? e.userMessage() : 'Failed to create rule');
    } finally {
      setSubmitting(false);
    }
  }

  if (!open) return null;

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal card">
        <header className="modal-header">
          <h2>New business rule</h2>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>✕</button>
        </header>

        <form className="modal-body form-stack" onSubmit={handleSubmit}>
          <label className="form-field">
            <span>Code</span>
            <input
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="BR-CUST-EMAIL-001"
            />
          </label>

          <label className="form-field">
            <span>Dimension</span>
            <select value={dimensionId} onChange={(e) => setDimensionId(e.target.value)}>
              <option value="">— none —</option>
              {dimensions.map((d) => (
                <option key={d.id} value={d.id}>{d.code} — {d.name}</option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>EDE mapping (optional)</span>
            <input
              value={edeMapping}
              onChange={(e) => setEdeMapping(e.target.value)}
              placeholder="EDE-CUSTOMER-EMAIL"
            />
          </label>

          <div className="form-field">
            <div className="form-field-row">
              <span>Short description (seed for AI)</span>
              <AIGenerateButton seed={seed} onGenerate={handleGenerate} />
            </div>
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              placeholder="What should the rule check, on which data?"
            />
          </div>

          <label className="form-field">
            <span>Rule text {streaming && <em className="muted">(streaming…)</em>}</span>
            <textarea
              required
              rows={6}
              value={ruleText}
              onChange={(e) => setRuleText(e.target.value)}
              placeholder="The generated rule will appear here. You can edit it before saving."
            />
          </label>

          {submitError && <div className="form-error">{submitError}</div>}

          <footer className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting || streaming}>
              {submitting ? 'Saving…' : 'Save rule'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
