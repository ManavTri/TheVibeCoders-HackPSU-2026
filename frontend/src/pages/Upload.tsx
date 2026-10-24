import { useRef, useState } from 'react'
import type { ChangeEvent, FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { useDocuments } from '../hooks/useDocuments'
import { documentTypeLabels } from '../lib/utils'
import type { DocumentType } from '../types/api'

interface SelectedFile {
  file: File
  type: DocumentType
}

const types = Object.keys(documentTypeLabels) as DocumentType[]

export function Upload() {
  const [selected, setSelected] = useState<SelectedFile[]>([])
  const { analyze: runAnalysis, busy, error, setError } = useDocuments()
  const inputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  function addFiles(files: FileList | null) {
    if (!files) return
    const pdfs = Array.from(files).filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    if (pdfs.length !== files.length) setError('Only PDF documents are supported.')
    setSelected((current) => [...current, ...pdfs.map((file) => ({ file, type: 'award_letter' as DocumentType }))])
  }

  function updateType(index: number, event: ChangeEvent<HTMLSelectElement>) {
    setSelected((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, type: event.target.value as DocumentType } : item))
  }

  async function analyze(event: FormEvent) {
    event.preventDefault()
    setError('')
    if (selected.length < 2) {
      setError('Add at least two PDFs to compare.')
      return
    }
    const report = await runAnalysis(selected.map((item) => item.file), selected.map((item) => item.type))
    if (report) navigate(`/report/${report.id}`)
  }

  return (
    <main className="content-page page-wrap upload-page">
      <Link to="/dashboard" className="back-link">← Your overview</Link>
      <div className="upload-heading"><div className="eyebrow">A CLEARER VIEW STARTS HERE</div><h1>Let’s connect<br />the <span>paperwork.</span></h1><p>Add two or more financial PDFs and we’ll surface details that may deserve a second look.</p></div>
      <form className="upload-form" onSubmit={analyze}>
        <div className="dropzone" onClick={() => inputRef.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); addFiles(event.dataTransfer.files) }}>
          <input ref={inputRef} type="file" accept=".pdf,application/pdf" multiple hidden onChange={(event) => addFiles(event.target.files)} />
          <div className="upload-glyph">↑</div><strong>Drop your PDFs here</strong><span>or <button type="button" className="inline-link" onClick={(event) => { event.stopPropagation(); inputRef.current?.click() }}>browse files</button> · PDF up to 10 MB each</span>
        </div>
        {selected.length > 0 && <div className="selected-list">
          <div className="selected-heading"><span>YOUR DOCUMENTS</span><span>{selected.length} added</span></div>
          {selected.map((item, index) => <div className="selected-file" key={`${item.file.name}-${index}`}>
            <span className="file-icon">PDF</span><span className="file-name">{item.file.name}<small>{(item.file.size / 1024 / 1024).toFixed(2)} MB</small></span>
            <label className="type-select"><span className="visually-hidden">Document type for {item.file.name}</span><select value={item.type} onChange={(event) => updateType(index, event)}>{types.map((type) => <option value={type} key={type}>{documentTypeLabels[type]}</option>)}</select></label>
            <button type="button" className="remove-file" aria-label={`Remove ${item.file.name}`} onClick={() => setSelected((current) => current.filter((_, itemIndex) => itemIndex !== index))}>×</button>
          </div>)}
        </div>}
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="upload-actions"><Button type="submit" disabled={busy}>{busy ? 'Reading your documents…' : 'Analyze documents'} <span aria-hidden="true">↗</span></Button><span>Files are processed by this demo API and not retained as uploaded files.</span></div>
      </form>
      <div className="privacy-strip"><span>◈</span><p><b>Your documents deserve care.</b> Use synthetic or non-sensitive PDFs with this demo. Reports are temporary and disappear when the API restarts.</p></div>
    </main>
  )
}
