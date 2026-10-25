import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { DocumentCard } from '../components/DocumentCard'
import { deleteDocument, getDocuments } from '../lib/api'
import type { DocumentRecord } from '../types/api'

export function Dashboard() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    getDocuments().then(setDocuments).catch((cause: unknown) => setError(cause instanceof Error ? cause.message : 'Could not load documents.'))
  }, [])

  async function removeDocument(id: string) {
    try {
      await deleteDocument(id)
      setDocuments((current) => current.filter((document) => document.id !== id))
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not delete this document.')
    }
  }

  return (
    <main className="content-page page-wrap">
      <div className="page-heading">
        <div><div className="eyebrow">YOUR MONEY, IN CONTEXT</div><h1>Good to see you.</h1><p>Bring your award letters and bills together for a clearer view.</p></div>
        <Link className="button button-primary" to="/upload">+ New document check</Link>
      </div>
      <section className="dashboard-grid">
        <article className="dashboard-feature">
          <div className="feature-art"><span className="feature-star">✳</span><div className="mini-paper"><b>$12,000</b><span>award amount</span><i>✓</i></div></div>
          <div className="eyebrow">START WITH A QUICK CHECK</div>
          <h2>Make the fine print<br />feel a little less fine.</h2>
          <p>Compare a scholarship, tuition bill, or program quote. We’ll point out details that may be worth confirming.</p>
          <Link className="text-link" to="/upload">Compare documents <span>→</span></Link>
        </article>
        <aside className="dashboard-side">
          <div className="eyebrow">HOW IT WORKS</div>
          <div className="how-item"><span>01</span><div><b>Add your documents</b><p>PDFs from your school, scholarship provider, or program.</p></div></div>
          <div className="how-item"><span>02</span><div><b>We look for mismatches</b><p>Amounts, terms, dates, and credit requirements.</p></div></div>
          <div className="how-item"><span>03</span><div><b>Get questions to ask</b><p>Know what to follow up on with your financial-aid office.</p></div></div>
          <div className="demo-callout"><span>✦</span><p>New here? Try the synthetic sample PDFs from our demo scenario.</p></div>
        </aside>
      </section>
      {error && <p className="form-error" role="alert">{error}</p>}
      {documents.length > 0 && <section className="dashboard-documents">
        <div className="section-title"><div><div className="eyebrow">YOUR PRIVATE DOCUMENTS</div><h2>Document library</h2></div><span>{documents.length} saved</span></div>
        <div className="dashboard-document-list">{documents.map((document) => <div className="dashboard-document-row" key={document.id}>
          <div className="dashboard-document-main"><DocumentCard document={document} />{document.extraction_error && <p className="document-error">{document.extraction_error}</p>}</div>
          <div className="document-row-actions"><span className={`document-status status-${document.status}`}>{document.status}</span><button type="button" className="remove-file" aria-label={`Delete ${document.filename}`} onClick={() => removeDocument(document.id)}>×</button></div>
        </div>)}</div>
      </section>}
      <footer className="site-footer"><span>Muni © 2026</span><span>For planning support—not financial advice.</span><Link to="/">Back to home</Link></footer>
    </main>
  )
}
