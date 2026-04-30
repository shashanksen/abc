import { WorkflowActionGroup } from '@/components/dq/WorkflowActionGroup';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { technicalRules } from '@/modules/dq/mockData';

export default function TechnicalRulesPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        title={`Technical Rules (${technicalRules.length})`}
        description="Approved business rules become implementation-ready technical rules with export targets such as dbt, SQL, and PySpark."
        actions={<button type="button" className="btn btn-primary">New technical rule</button>}
      />

      <div className="inline-note">
        Consistency and accuracy dimensions may require selection of two CDEs. The implementation step will later open a workflow for connection details, frequency, and pipeline deployment settings.
      </div>

      <div className="card table-scroll">
        <table>
          <thead>
            <tr>
              <th>EDE ID</th>
              <th>EDE Name</th>
              <th>DQ Dimension</th>
              <th>CDE Coverage</th>
              <th>Business Rule</th>
              <th>Technical Rule</th>
              <th>Version</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {technicalRules.map((rule) => (
              <tr key={rule.id}>
                <td className="mono">{rule.edeId}</td>
                <td>{rule.edeName}</td>
                <td>{rule.dqDimension}</td>
                <td>
                  <div className="table-cell-stack">
                    <div className="table-list">
                      {rule.cdeIds.map((item) => (
                        <span key={item} className="chip chip-primary mono">{item}</span>
                      ))}
                    </div>
                    <span className="surface-row-meta">{rule.cdeNames.join(', ')}</span>
                  </div>
                </td>
                <td>{rule.businessRule}</td>
                <td>
                  <div className="table-cell-stack">
                    <span className="mono">{rule.technicalRule}</span>
                    <span className="surface-row-meta">Target: {rule.implementationTarget}</span>
                  </div>
                </td>
                <td>{rule.version}</td>
                <td><StatusBadge status={rule.status} /></td>
                <td><WorkflowActionGroup actions={rule.actions} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
