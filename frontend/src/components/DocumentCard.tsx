import type { DocumentSummary } from '../types/api'
import { documentTypeLabels, formatDate, formatMoney } from '../lib/utils'

export function DocumentCard({ document }: { document: DocumentSummary }) {
  return (
    <article className="document-card">
      <div className="document-icon" aria-hidden="true">{document.document_type === 'award_letter' ? '$' : '▤'}</div>
      <div className="document-info">
        <span className="eyebrow">{documentTypeLabels[document.document_type]}</span>
        <strong>{document.filename}</strong>
        <div className="document-fields">
          <span>{formatMoney(document.amount, document.currency)}</span>
          <span>{document.term || 'Term not found'}</span>
          {document.deadline && <span>Due {formatDate(document.deadline)}</span>}
          {document.required_credits !== null && <span>{document.required_credits} credits</span>}
        </div>
      </div>
      <span className="document-check" aria-label="Document reviewed">✓</span>
    </article>
  )
}
