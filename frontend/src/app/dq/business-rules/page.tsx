'use client';

/**
 * Business rules page — wired to the real backend and the AI generate flow.
 *
 * Differences from the earlier mock-data version:
 *   - List comes from /api/dq/business-rules (not mockData.businessRules)
 *   - "New business rule" opens a modal with an AI generate button
 *   - On save: POST /api/dq/business-rules; on success the list refreshes
 *
 * The mock data still exists in mockData.ts and is used by other DQ pages
 * (dimensions, ede-mappings, technical-rules) — we don't break them.
 */
import { useEffect, useState } from 'react';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { dqApi, type BusinessRule } from '@/modules/dq/api';
import { ApiError } from '@/lib/errors';
import { CreateBusinessRuleModal } from './CreateBusinessRuleModal';

export default function BusinessRulesPage() {
  const [rules, setRules]     = useState<BusinessRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = () => {
    setLoading(true);
    setError(null);
    dqApi.listBusinessRules()
      .then((rows) => { setRules(rows); setLoading(false); })
      .catch((e) => {
        setLoading(false);
        setError(e instanceof ApiError ? e.userMessage() : 'Failed to load business rules');
      });
  };

  useEffect(load, []);

  return (
    <div className="page-stack">
      <SectionHeader
        title={loading ? 'Business rules' : `Business rules (${rules.length})`}
        description="Analysts generate business rules from mapped EDEs, then route them through BU and Central CDO approvals."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreate(true)}>
            New business rule
          </button>
        }
      />

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="content-card card-body">
          <p className="muted">Loading…</p>
        </div>
      ) : rules.length === 0 ? (
        <div className="content-card card-body">
          <p className="muted">
            No business rules yet. Click <strong>New business rule</strong> to draft one — you can use the AI helper to generate the rule text from a short description.
          </p>
        </div>
      ) : (
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>Code</th>
                <th>EDE mapping</th>
                <th>Rule text</th>
                <th>Status</th>
                <th>Version</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.id}>
                  <td className="mono">{rule.code}</td>
                  <td>{rule.ede_mapping || '-'}</td>
                  <td style={{ maxWidth: 480 }}>
                    <div style={{ whiteSpace: 'pre-wrap' }}>{rule.rule_text}</div>
                  </td>
                  <td><StatusBadge status={rule.status} /></td>
                  <td>{rule.version}</td>
                  <td>{new Date(rule.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateBusinessRuleModal
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={() => { setShowCreate(false); load(); }}
      />
    </div>
  );
}
