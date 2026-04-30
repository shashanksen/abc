import { WorkflowActionGroup } from '@/components/dq/WorkflowActionGroup';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { dimensions } from '@/modules/dq/mockData';

export default function DimensionsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        title={`DQ Dimensions (${dimensions.length})`}
        description="Dimension records are the foundation of the workflow. Generate, edit, and approve them before downstream rule generation."
        actions={<button type="button" className="btn btn-primary">New dimension</button>}
      />

      <div className="split-grid">
        <div className="card table-scroll">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>DQ Dimension</th>
                <th>Definition</th>
                <th>Version</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {dimensions.map((dimension) => (
                <tr key={dimension.id}>
                  <td className="mono">{dimension.id}</td>
                  <td>
                    <div className="table-cell-stack">
                      <span className="surface-row-title">{dimension.name}</span>
                      <span className="surface-row-meta mono">{dimension.code}</span>
                    </div>
                  </td>
                  <td>{dimension.definition}</td>
                  <td>{dimension.version}</td>
                  <td>
                    <div className="table-cell-stack">
                      <StatusBadge status={dimension.status} />
                      <span className="surface-row-meta">Owner: {dimension.owner}</span>
                    </div>
                  </td>
                  <td>
                    <WorkflowActionGroup actions={dimension.actions} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <aside className="content-card section-stack">
          <div className="stack-sm">
            <div className="eyebrow-text">Governance note</div>
            <p className="muted">
              The BA flow expects DQ Analysts to generate dimensions, BU CDOs to review them, and Central CDO to finalize them before rule work starts.
            </p>
          </div>
          <div className="stack-sm">
            <div className="eyebrow-text">Current focus</div>
            <div className="surface-list">
              {dimensions.map((dimension) => (
                <div key={dimension.id} className="surface-row">
                  <div>
                    <div className="surface-row-title">{dimension.name}</div>
                    <div className="surface-row-meta">Updated {dimension.lastUpdated}</div>
                  </div>
                  <StatusBadge status={dimension.status} />
                </div>
              ))}
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
