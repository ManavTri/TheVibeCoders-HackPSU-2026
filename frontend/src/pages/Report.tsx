import { Link, useNavigate, useParams } from 'react-router-dom'
import { DocumentCorrectionForm } from '../components/DocumentCorrectionForm'
import { FindingCard } from '../components/FindingCard'
import { InsightsPanel } from '../components/InsightsPanel'
import { SideBySideViewer } from '../components/SideBySideViewer'
import { correctDocument, createValidation } from '../lib/api'
import { useReport } from '../hooks/useReport'
import type { DocumentType } from '../types/api'

export function Report() {
  const { id = '' } = useParams()
  const { report, insights, error } = useReport(id)
  const navigate = useNavigate()

  async function saveCorrection(documentId: string, correction: {
    amount: number | null
    term: string | null
    deadline: string | null
    required_credits: number | null
    document_type: DocumentType
  }) {
    if (!report) throw new Error('Report has not loaded yet.')
    await correctDocument(documentId, correction)
    const newReport = await createValidation(report.documents.map((document) => document.id))
    navigate(`/report/${newReport.id}`)
  }

  if (error) return <main className="content-page page-wrap"><p className="form-error" role="alert">{error}</p><Link className="button button-primary" to="/upload">Start a new check</Link></main>
  if (!report || !insights) return <main className="content-page page-wrap loading-state"><div className="loader" /><p>Putting your documents side by side…</p></main>

  return (
    <main className="content-page page-wrap report-page">
      <div className="report-topline"><Link to="/dashboard" className="back-link">← Overview</Link><Link to="/upload" className="text-link">New check ↗</Link></div>
      <div className="report-heading">
        <div><div className="eyebrow">YOUR DOCUMENT CHECK · {new Date(report.created_at).toLocaleDateString()}</div><h1>{report.findings.length ? 'A few things to look at.' : 'Looking clear so far.'}</h1><p>{report.summary} Here’s what showed up across your documents.</p></div>
        <div className="report-score"><span>{String(report.findings.length).padStart(2, '0')}</span><small>details<br />to review</small></div>
      </div>
      <section className="report-section"><div className="section-title"><div><div className="eyebrow">THE DOCUMENTS</div><h2>Side by side</h2></div><span>{report.documents.length} documents checked</span></div><SideBySideViewer documents={report.documents} /></section>
      <section className="report-section correction-section"><div className="section-title"><div><div className="eyebrow">YOU KNOW YOUR DOCUMENTS BEST</div><h2>Correct an extracted field</h2></div><span>We’ll run the checks again after you save.</span></div>
        <div className="correction-list">{report.documents.map((document) => <DocumentCorrectionForm key={document.id} document={document} onSave={saveCorrection} />)}</div>
      </section>
      <section className="report-section findings-section"><div className="section-title"><div><div className="eyebrow">WHAT CAUGHT OUR EYE</div><h2>Worth a second look</h2></div><span>Potential mismatches, not financial advice</span></div>
        {report.findings.length > 0 ? <div className="finding-list">{report.findings.map((finding, index) => <FindingCard key={`${finding.rule_id}-${index}`} finding={finding} index={index} />)}</div> : <div className="empty-findings"><span>✓</span><div><b>No potential inconsistencies found.</b><p>We could not detect a conflict in the fields we read. Missing fields may still need manual review.</p></div></div>}
      </section>
      <section className="report-section"><InsightsPanel insights={insights} /></section>
      <footer className="site-footer"><span>ClearLedger © 2026</span><span>Confirm details with your financial-aid office or provider.</span><Link to="/">Home</Link></footer>
    </main>
  )
}
