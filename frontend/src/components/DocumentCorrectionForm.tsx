import { useState } from 'react'
import type { FormEvent } from 'react'
import type { DocumentSummary, DocumentType } from '../types/api'
import { documentTypeLabels } from '../lib/utils'

const documentTypes = Object.keys(documentTypeLabels) as DocumentType[]

export function DocumentCorrectionForm({
  document,
  onSave,
}: {
  document: DocumentSummary
  onSave: (documentId: string, correction: {
    amount: number | null
    term: string | null
    deadline: string | null
    required_credits: number | null
    document_type: DocumentType
  }) => Promise<void>
}) {
  const [amount, setAmount] = useState(document.amount === null ? '' : String(document.amount))
  const [term, setTerm] = useState(document.term || '')
  const [deadline, setDeadline] = useState(document.deadline || '')
  const [credits, setCredits] = useState(document.required_credits === null ? '' : String(document.required_credits))
  const [documentType, setDocumentType] = useState(document.document_type)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setBusy(true)
    try {
      await onSave(document.id, {
        amount: amount ? Number(amount) : null,
        term: term || null,
        deadline: deadline || null,
        required_credits: credits ? Number(credits) : null,
        document_type: documentType,
      })
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not save this correction.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <details className="correction-card">
      <summary>Correct extracted fields · {document.filename}</summary>
      <form onSubmit={submit}>
        <label>Document type<select value={documentType} onChange={(event) => setDocumentType(event.target.value as DocumentType)}>{documentTypes.map((type) => <option key={type} value={type}>{documentTypeLabels[type]}</option>)}</select></label>
        <label>Amount<input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
        <label>Academic term<input value={term} onChange={(event) => setTerm(event.target.value)} placeholder="Fall 2026" /></label>
        <label>Deadline<input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label>
        <label>Required credits<input type="number" min="0" step="1" value={credits} onChange={(event) => setCredits(event.target.value)} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="button button-secondary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save corrections and re-check'}</button>
      </form>
    </details>
  )
}
