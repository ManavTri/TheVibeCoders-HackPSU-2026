import type { Finding } from '../types/api'

export function FindingCard({ finding, index }: { finding: Finding; index: number }) {
  return (
    <article className={`finding-card severity-${finding.severity}`}>
      <div className="finding-number">{String(index + 1).padStart(2, '0')}</div>
      <div>
        <div className="finding-meta">
          <span className={`severity-pill ${finding.severity}`}>{finding.severity} priority</span>
          <code>{finding.rule_id}</code>
        </div>
        <h3>{finding.title}</h3>
        <p>{finding.message}</p>
      </div>
      <span className="finding-arrow" aria-hidden="true">↗</span>
    </article>
  )
}
