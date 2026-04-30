import { WorkflowActionGroup } from '@/components/dq/WorkflowActionGroup';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { edeMappings } from '@/modules/dq/mockData';

export default function EdeMappingsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        title="EDE Mappings"
        description="Bootstrap enterprise data element mappings from spreadsheet uploads now, then swap to glossary integration later."
      />

      <section className="content-card upload-panel">
        <div className="upload-dropzone">
          <div className="stack-sm">
            <div className="surface-row-title">Upload EDE to CDE mapping file</div>
            <div className="surface-row-meta">Expected columns: EDE ID, EDE Name, EDE definition, CDE ID, CDE Name, System name, Database name, attribute.</div>
          </div>
          <WorkflowActionGroup actions={['Upload']} />
        </div>

        <div className="inline-note">
          Ideally this screen will integrate with the business glossary later. For the first release, this page acts as the upload and review workspace for EDW to CDE to attribute mapping coverage.
        </div>
      </section>

      <div className="card table-scroll">
        <table>
          <thead>
            <tr>
              <th>EDE ID</th>
              <th>EDE Name</th>
              <th>EDE Definition</th>
              <th>CDE ID</th>
              <th>CDE Name</th>
              <th>System</th>
              <th>Database</th>
              <th>Attribute</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {edeMappings.map((mapping) => (
              <tr key={`${mapping.edeId}-${mapping.cdeId}`}>
                <td className="mono">{mapping.edeId}</td>
                <td>{mapping.edeName}</td>
                <td>{mapping.edeDefinition}</td>
                <td className="mono">{mapping.cdeId}</td>
                <td>{mapping.cdeName}</td>
                <td>{mapping.systemName}</td>
                <td>{mapping.databaseName}</td>
                <td>{mapping.attribute}</td>
                <td><StatusBadge status={mapping.status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
