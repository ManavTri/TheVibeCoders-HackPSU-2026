import type { Insights } from '../types/api'

export function InsightsPanel({ insights }: { insights: Insights }) {
  return (
    <aside className="insights-panel">
      <div className="insights-mark" aria-hidden="true">✳</div>
      <div className="eyebrow">Your next move</div>
      <h2>{insights.headline}</h2>
      <ul>
        {insights.recommendations.map((item) => <li key={item}>{item}</li>)}
      </ul>
      <p className="disclaimer">{insights.disclaimer}</p>
    </aside>
  )
}
