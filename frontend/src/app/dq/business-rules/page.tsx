import { WorkflowActionGroup } from '@/components/dq/WorkflowActionGroup';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { businessRules } from '@/modules/dq/mockData';

export default function BusinessRulesPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        title={`Business Rules (${businessRules.length})`}
        description="Analysts generate business rules from mapped EDEs, then route them through BU and Central CDO approvals."
        actions={<button type="button" className="btn btn-primary">New business rule</button>}
      />

      <div className="card table-scroll">
        <table>
          <thead>
            <tr>
              <th>EDE ID</th>
              <th>EDE Name</th>
              <th>DQ Dimension</th>
              <th>Business Rule Design</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {businessRules.map((rule) => (
              <tr key={rule.id}>
                <td className="mono">{rule.edeId}</td>
                <td>{rule.edeName}</td>
                <td>{rule.dqDimension}</td>
                <td>
                  <div className="table-cell-stack">
                    <span><strong>Input:</strong> {rule.input}</span>
                    <span><strong>Objective:</strong> {rule.objective}</span>
                    <span><strong>Definition:</strong> {rule.ruleDefinition}</span>
                    <span><strong>Guidelines:</strong> {rule.guidelines}</span>
                    <span><strong>Acceptance:</strong> {rule.acceptanceCriteria}</span>
                  </div>
                </td>
                <td>
                  <div className="table-cell-stack">
                    <StatusBadge status={rule.status} />
                    <span className="surface-row-meta">Owner: {rule.owner}</span>
                  </div>
                </td>
                <td>
                  <WorkflowActionGroup actions={rule.actions} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
