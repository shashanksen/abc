'use client';

import { useMemo, useState } from 'react';
import { DqMetricCard } from '@/components/dq/DqMetricCard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { dimensions, edeMappings, outcomes } from '@/modules/dq/mockData';

export default function DqDashboardPage() {
  const [selectedDimension, setSelectedDimension] = useState('All');
  const [selectedEde, setSelectedEde] = useState('All');

  const filteredOutcomes = useMemo(
    () =>
      outcomes.filter((item) => {
        const matchesDimension = selectedDimension === 'All' || item.dqDimension === selectedDimension;
        const matchesEde = selectedEde === 'All' || item.edeName === selectedEde;
        return matchesDimension && matchesEde;
      }),
    [selectedDimension, selectedEde]
  );

  const averageScore = filteredOutcomes.length
    ? filteredOutcomes.reduce((total, item) => total + item.passRate, 0) / filteredOutcomes.length
    : 0;

  return (
    <div className="page-stack">
      <SectionHeader
        title="DQ Dashboard"
        description="Outcome reporting by DQ dimension and enterprise data element after rules are implemented."
      />

      <section className="content-card section-stack">
        <div className="filter-bar">
          <div className="form-group filter-field">
            <label className="form-label" htmlFor="dq-dimension-filter">DQ Dimension</label>
            <select
              id="dq-dimension-filter"
              className="form-select"
              value={selectedDimension}
              onChange={(event) => setSelectedDimension(event.target.value)}
            >
              <option value="All">All dimensions</option>
              {dimensions.map((dimension) => (
                <option key={dimension.id} value={dimension.name}>{dimension.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group filter-field">
            <label className="form-label" htmlFor="dq-ede-filter">EDE</label>
            <select
              id="dq-ede-filter"
              className="form-select"
              value={selectedEde}
              onChange={(event) => setSelectedEde(event.target.value)}
            >
              <option value="All">All EDEs</option>
              {edeMappings.map((mapping) => (
                <option key={mapping.edeId} value={mapping.edeName}>{mapping.edeName}</option>
              ))}
            </select>
          </div>
        </div>

        <div className="stats-grid">
          <DqMetricCard label="Visible controls" value={String(filteredOutcomes.length)} meta="Filtered dashboard rows" />
          <DqMetricCard label="Average pass rate" value={`${averageScore.toFixed(1)}%`} meta="Across current selection" />
          <DqMetricCard label="Open issues" value={String(filteredOutcomes.reduce((sum, item) => sum + item.issueCount, 0))} meta="Exceptions awaiting remediation" />
          <DqMetricCard label="Live pipelines" value={String(new Set(filteredOutcomes.map((item) => item.platform)).size)} meta="Implementation targets represented" />
        </div>
      </section>

      <div className="card table-scroll">
        <table>
          <thead>
            <tr>
              <th>DQ Dimension</th>
              <th>EDE</th>
              <th>Pass rate</th>
              <th>Trend</th>
              <th>Open issues</th>
              <th>Platform</th>
              <th>Last run</th>
            </tr>
          </thead>
          <tbody>
            {filteredOutcomes.map((outcome) => (
              <tr key={outcome.id}>
                <td>{outcome.dqDimension}</td>
                <td>{outcome.edeName}</td>
                <td>{outcome.passRate.toFixed(1)}%</td>
                <td><StatusBadge status={outcome.trend} /></td>
                <td>{outcome.issueCount}</td>
                <td>{outcome.platform}</td>
                <td>{outcome.lastRun}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
