import { useState } from 'react'
import type { FormEvent } from 'react'
import { correctDocument } from '../lib/api'
import { documentTypeLabels } from '../lib/utils'
import type { DocumentCorrection, DocumentRecord, DocumentType } from '../types/api'

const documentTypes = Object.keys(documentTypeLabels) as DocumentType[]
type EditableField = 'amount' | 'currency' | 'term' | 'deadline' | 'required_credits'

function foundFields(document: DocumentRecord): EditableField[] {
  const envelope = document.extraction_envelope
  return [
    ...(document.amount !== null ? ['amount' as const] : []),
    ...(typeof envelope?.currency === 'string' ? ['currency' as const] : []),
    ...(document.term ? ['term' as const] : []),
    ...(document.deadline ? ['deadline' as const] : []),
    ...(document.required_credits !== null ? ['required_credits' as const] : []),
  ]
}

export function UploadDocumentReview({
  document,
  onSaved,
}: {
  document: DocumentRecord
  onSaved: (updated: DocumentRecord) => void
}) {
  const [documentType, setDocumentType] = useState(document.document_type)
  const [amount, setAmount] = useState(document.amount === null ? '' : String(document.amount))
  const [currency, setCurrency] = useState(document.currency)
  const [term, setTerm] = useState(document.term || '')
  const [deadline, setDeadline] = useState(document.deadline || '')
  const [credits, setCredits] = useState(document.required_credits === null ? '' : String(document.required_credits))
  const [showAllFields, setShowAllFields] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const found = foundFields(document)
  const visible = new Set<EditableField>(showAllFields
    ? ['amount', 'currency', 'term', 'deadline', 'required_credits']
    : found)

  async function save(event: FormEvent) {
    event.preventDefault()
    setError('')
    const correction: DocumentCorrection = {}
    if (documentType !== document.document_type) correction.document_type = documentType
    if (visible.has('amount') && amount !== (document.amount === null ? '' : String(document.amount))) {
      correction.amount = amount ? Number(amount) : null
    }
    if (visible.has('currency') && currency !== document.currency) correction.currency = currency.toUpperCase()
    if (visible.has('term') && term !== (document.term || '')) correction.term = term || null
    if (visible.has('deadline') && deadline !== (document.deadline || '')) correction.deadline = deadline || null
    if (visible.has('required_credits') && credits !== (document.required_credits === null ? '' : String(document.required_credits))) {
      correction.required_credits = credits ? Number(credits) : null
    }
    if (!Object.keys(correction).length) {
      setError('There are no changes to save.')
      return
    }

    setBusy(true)
    try {
      onSaved(await correctDocument(document.id, correction))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save these extracted fields.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <article className="upload-review-card">
      <div className="upload-review-heading">
        <div>
          <span className="file-icon">PDF</span>
          <div><strong>{document.filename}</strong><small>{document.status === 'extracted' ? 'Extraction complete' : document.extraction_error || 'Extraction failed'}</small></div>
        </div>
        <span className={`document-status status-${document.status}`}>{document.status}</span>
      </div>
      {document.status === 'extracted' && (
        <form onSubmit={save}>
          <label>
            Gemini’s document type
            <select value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)}>
              {documentTypes.map((type) => <option value={type} key={type}>{documentTypeLabels[type]}</option>)}
            </select>
          </label>
          <p className="type-detection-note">
            {document.extraction_source === 'gemini' ? 'Identified by Gemini' : 'Identified by text extraction'}
            {document.type_confidence !== null && document.type_confidence !== undefined
              ? ` · ${Math.round(document.type_confidence * 100)}% confidence`
              : ''}
            . You can correct the type before checking.
          </p>
          <div className="upload-review-fields">
            {visible.has('amount') && <label>Amount<input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>}
            {visible.has('currency') && <label>Currency<input maxLength={3} value={currency} onChange={(event) => setCurrency(event.target.value.toUpperCase())} /></label>}
            {visible.has('term') && <label>Academic term<input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Fall 2026" /></label>}
            {visible.has('deadline') && <label>Deadline<input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label>}
            {visible.has('required_credits') && <label>Required credits<input type="number" min="0" step="1" value={credits} onChange={(event) => setCredits(event.target.value)} /></label>}
          </div>
          {found.length < 5 && <button className="inline-link review-more-fields" type="button" onClick={() => setShowAllFields((value) => !value)}>{showAllFields ? 'Hide fields not found' : 'Add or edit other fields'}</button>}
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="button button-secondary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save changes'}</button>
        </form>
      )}
    </article>
  )
}
