import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UploadDocumentReview } from '../components/UploadDocumentReview'
import { Button } from '../components/ui/Button'
import { useDocuments } from '../hooks/useDocuments'
import type { DocumentRecord } from '../types/api'

interface SelectedFile {
  file: File
}

export function Upload() {
  const [selected, setSelected] = useState<SelectedFile[]>([])
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const { upload, validate, busy, error, setError } = useDocuments()
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  function addFiles(files: FileList | null) {
    if (!files) return
    const pdfs = Array.from(files).filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== files.length) setError('Only PDF documents are supported.')
    setSelected((current) => [...current, ...pdfs.map((file) => ({ file }))])
  }

  async function uploadFiles(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (selected.length === 0) {
      setError('Add at least one PDF to upload.')
      return
    }
    const result = await upload(
      selected.map((item) => item.file),
    )
    if (result) {
      setDocuments((current) => [...result.documents, ...current])
      setSelected((current) => current.filter((item) => result.failedFiles.includes(item.file)))
      if (result.failedFiles.length === 0 && inputRef.current) inputRef.current.value = ''
    }
  }

  async function analyze() {
    setError('')
    const extracted = documents.filter((document) => document.status === 'extracted')
    if (extracted.length < 2) {
      setError('At least two successfully extracted documents are needed to run a check.')
      return
    }
    const report = await validate(extracted.map((document) => document.id))
    if (report) navigate(`/report/${report.id}`)
  }

  function updateDocument(updated: DocumentRecord) {
    setDocuments((current) => current.map((document) => document.id === updated.id ? updated : document))
  }

  return (
    <main className="content-page page-wrap upload-page">
      <Link to="/dashboard" className="back-link">← Your overview</Link>
      <div className="upload-heading"><div className="eyebrow">A CLEARER VIEW STARTS HERE</div><h1>Let’s connect<br />the <span>paperwork.</span></h1><p>Add two or more financial PDFs. We’ll identify each document and let you review what we read before checking for inconsistencies.</p></div>
      <form className="upload-form" onSubmit={uploadFiles}>
        <div className="dropzone" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); addFiles(event.dataTransfer.files) }}>
          <input ref={inputRef} type="file" accept=".pdf,application/pdf" multiple hidden onChange={(event) => addFiles(event.target.files)} />
          <div className="upload-glyph">↑</div><strong>Drop your PDFs here</strong><span>or <button type="button" className="inline-link" onClick={(event) => { event.stopPropagation(); inputRef.current?.click() }}>browse files</button> · PDF up to 10 MB each</span>
        </div>
        {selected.length > 0 && <div className="selected-list">
          <div className="selected-heading"><span>READY TO UPLOAD</span><span>{selected.length} added</span></div>
          {selected.map((item, index) => <div className="selected-file" key={`${item.file.name}-${index}`}>
            <span className="file-icon">PDF</span><span className="file-name">{item.file.name}<small>{(item.file.size / 1024 / 1024).toFixed(2)} MB</small></span>
            <button type="button" className="remove-file" aria-label={`Remove ${item.file.name}`} onClick={() => setSelected((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button>
          </div>)}
        </div>}
        {selected.length > 0 && <div className="upload-actions"><Button type="submit" disabled={busy}>{busy ? 'Reading your documents…' : 'Upload and review'} <span aria-hidden="true">↗</span></Button><span>Muni classifies each document from its contents. You can correct the type after upload.</span></div>}
      </form>

      {documents.length > 0 && <section className="upload-review-section">
        <div className="section-title"><div><div className="eyebrow">REVIEW BEFORE CHECKING</div><h2>Your extracted documents</h2></div><span>{documents.filter((document) => document.status === 'extracted').length} ready</span></div>
        <p className="upload-review-intro">Gemini’s classification is shown for each file. Correct the type or any extracted fields before running the comparison.</p>
        <div className="upload-review-list">
          {documents.map((document) => <UploadDocumentReview key={document.id} document={document} onSaved={updateDocument} />)}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="upload-actions"><Button type="button" onClick={analyze} disabled={busy}>{busy ? 'Comparing documents…' : 'Check these documents'} <span aria-hidden="true">↗</span></Button><span>At least two documents must finish extraction to run a check.</span></div>
      </section>}
      {!documents.length && error && <p className="form-error upload-form-error" role="alert">{error}</p>}
      <div className="privacy-strip"><span>◈</span><p><b>Your documents deserve care.</b> Documents are private to your account. Review extracted fields before relying on findings.</p></div>
    </main>
  )
}
