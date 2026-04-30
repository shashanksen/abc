'use client';

import { useState } from 'react';
import { DqMetricCard } from '@/components/dq/DqMetricCard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { businessRules, dimensions, edeMappings, outcomes, personas, personaTasks, technicalRules, type DqPersona } from '@/modules/dq/mockData';

const workflowSteps = [
  {
    step: '1. Generate business rules',
    owner: 'DQ Analyst',
    description: 'Create business rules from approved dimensions and mapped enterprise data elements.',
  },
  {
    step: '2. BU CDO approval',
    owner: 'BU CDO',
    description: 'Review generated business rules before they move to central governance approval.',
  },
  {
    step: '3. Central approval',
    owner: 'Central CDO',
    description: 'Approve enterprise-wide business rules and release them for technical rule generation.',
  },
  {
    step: '4. Generate and implement technical rules',
    owner: 'DQ Analyst / DQ Engineer',
    description: 'Convert approved business rules to dbt, SQL, or PySpark implementations and deploy them.',
  },
  {
    step: '5. Display outcomes',
    owner: 'DQ Dashboard',
    description: 'Track pass rate, issue count, and run history by dimension and EDE.',
  },
];

export default function DqDashboard() {
  const [selectedPersona, setSelectedPersona] = useState<DqPersona>('Central CDO');
  const visibleTasks = personaTasks.filter((task) => task.persona === selectedPersona);

  return (
    <div className="page-stack">
      <section className="page-stack">
        <div className="stats-grid">
          <DqMetricCard label="DQ Dimensions" value={String(dimensions.length)} meta="Governance foundations" />
          <DqMetricCard label="EDE Mappings" value={String(edeMappings.length)} meta="Mapped enterprise elements" />
          <DqMetricCard label="Business Rules" value={String(businessRules.length)} meta="Approval pipeline" />
          <DqMetricCard label="Technical Rules" value={String(technicalRules.length)} meta="Ready for implementation" />
        </div>

        <div className="split-grid">
          <article className="content-card">
            <SectionHeader
              title="Role-aware work queue"
              description="The BA flow expects each persona to see only its own pending work."
            />
            <div className="stack-sm">
              <div className="segment-control" role="tablist" aria-label="DQ personas">
                {personas.map((persona) => (
                  <button
                    key={persona}
                    type="button"
                    className={`segment-button${persona === selectedPersona ? ' active' : ''}`}
                    onClick={() => setSelectedPersona(persona)}
                  >
                    {persona}
                  </button>
                ))}
              </div>

              <div className="surface-list">
                {visibleTasks.map((task) => (
                  <div key={task.id} className="surface-row">
                    <div className="table-cell-stack">
                      <span className="surface-row-title">{task.title}</span>
                      <span className="surface-row-meta">{task.description}</span>
                    </div>
                    <div className="table-cell-stack">
                      <StatusBadge status={task.stage} />
                      <span className="surface-row-meta">{task.priority} priority · due {task.due}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </article>

          <article className="content-card">
            <SectionHeader
              title="Current pipeline snapshot"
              description="A frontend-first preview of the governed DQ flow you described."
            />
            <div className="workflow-lane-list">
              {workflowSteps.map((item) => (
                <div key={item.step} className="workflow-lane">
                  <div className="workflow-step">{item.owner}</div>
                  <div className="workflow-body">
                    <div className="surface-row-title">{item.step}</div>
                    <div className="surface-row-meta">{item.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="page-stack">
        <SectionHeader
          title="Outcome preview"
          description="The DQ dashboard will become the final step in the workflow after implementation."
        />
        <div className="grid-auto">
          {outcomes.map((outcome) => (
            <article key={outcome.id} className="content-card score-card">
              <span className="eyebrow-text">{outcome.dqDimension}</span>
              <h3 className="surface-row-title">{outcome.edeName}</h3>
              <div className={`score-value${outcome.passRate >= 99 ? ' success' : outcome.passRate >= 97 ? ' warning' : ' error'}`}>
                {outcome.passRate.toFixed(1)}%
              </div>
              <div className="surface-row-meta">
                {outcome.issueCount} open issues · last run {outcome.lastRun}
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
