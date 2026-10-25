import { useCallback, useEffect, useMemo, useState } from 'react'
import { DocumentDropzone } from './components/DocumentDropzone'
import { SectionCard } from './components/SectionCard'
import { Sidebar } from './components/Sidebar'
import { StatCard } from './components/StatCard'
import { FinancialChat } from './components/FinancialChat'
import {
  archiveDocument,
  correctDocument,
  createInsights,
  createValidation,
  getCurrentFindings,
  getDocumentPdf,
  getDocuments,
  getValidation,
  permanentlyDeleteDocument,
  remoteApiWithoutAuth,
  restoreDocument,
  softDeleteDocument,
  supabase,
  uploadDocument,
  authConfigurationIncomplete,
} from './lib/backend'

const states = ['active', 'archived', 'deleted']
const documentTypes = [
  ['award_letter', 'Award letter'],
  ['tuition_bill', 'Tuition bill'],
  ['study_abroad_quote', 'Study-abroad quote'],
]

function formatMoney(amount, currency = 'USD') {
  if (amount === null || amount === undefined || amount === '') return '—'
  const numericAmount = Number(amount)
  if (!Number.isFinite(numericAmount)) return '—'

  const currencyCode = typeof currency === 'string' && /^[A-Za-z]{3}$/.test(currency.trim())
    ? currency.trim().toUpperCase()
    : 'USD'
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: currencyCode }).format(numericAmount)
  } catch (error) {
    if (!(error instanceof RangeError)) throw error
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(numericAmount)
  }
}

function formatDate(value) {
  if (!value) return 'Date not found'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${value}T00:00:00Z`))
}

function typeLabel(type) {
  return documentTypes.find(([value]) => value === type)?.[1] || type
}

function errorText(error, fallback) {
  return error instanceof Error ? error.message : fallback
}

function fetchUserData() {
  return Promise.all([
    getDocuments('active'),
    getDocuments('archived'),
    getDocuments('deleted'),
    getCurrentFindings(),
  ]).then(([active, archived, deleted, currentFindings]) => ({
    active,
    archived,
    deleted,
    currentFindings,
  }))
}

function AuthPanel() {
  const [mode, setMode] = useState('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function submit(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      if (mode === 'signin') {
        const { error: authError } = await supabase.auth.signInWithPassword({ email, password })
        if (authError) throw authError
      } else {
        const { data, error: authError } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { name } },
        })
        if (authError) throw authError
        if (!data.session) setMessage('Check your email to confirm your account, then sign in.')
      }
    } catch (cause) {
      setError(errorText(cause, 'Authentication failed.'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto mt-10 max-w-md rounded-3xl border border-slate-800 bg-[#0b0e12] p-7 shadow-xl">
      <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Private student workspace</p>
      <h2 className="mt-3 text-3xl font-semibold text-white">{mode === 'signin' ? 'Welcome back' : 'Create your account'}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">Sign in with your Supabase account to securely manage your financial documents.</p>
      <form className="mt-6 space-y-4" onSubmit={submit}>
        {mode === 'signup' && <label className="block text-sm text-slate-300">Name
          <input className="mt-2 w-full rounded-xl border border-slate-700 bg-[#111821] px-3 py-2 text-white" value={name} onChange={(event) => setName(event.target.value)} required />
        </label>}
        <label className="block text-sm text-slate-300">Email
          <input className="mt-2 w-full rounded-xl border border-slate-700 bg-[#111821] px-3 py-2 text-white" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="block text-sm text-slate-300">Password
          <input className="mt-2 w-full rounded-xl border border-slate-700 bg-[#111821] px-3 py-2 text-white" type="password" minLength={8} autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        {error && <p className="rounded-xl bg-rose-950/50 p-3 text-sm text-rose-200" role="alert">{error}</p>}
        {message && <p className="rounded-xl bg-emerald-950/50 p-3 text-sm text-emerald-200" role="status">{message}</p>}
        <button className="w-full rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50" type="submit" disabled={busy}>
          {busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'}
        </button>
      </form>
      <p className="mt-5 text-center text-sm text-slate-400">
        {mode === 'signin' ? 'New to EduCash?' : 'Already have an account?'}{' '}
        <button className="font-semibold text-white underline" type="button" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); setMessage('') }}>
          {mode === 'signin' ? 'Create account' : 'Sign in'}
        </button>
      </p>
    </div>
  )
}

function DocumentRow({ document, onAction, onPreview, onEdit, busy }) {
  return (
    <article className="grid gap-4 rounded-2xl border border-slate-800 bg-[#0f141a] p-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
      <button type="button" className="min-w-0 text-left" onClick={() => onPreview(document)}>
        <div className="flex items-start gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-800 text-sm font-bold text-white">PDF</span>
          <span className="min-w-0">
            <span className="block truncate font-medium text-white">{document.filename}</span>
            <span className="mt-1 block text-xs text-slate-400">{typeLabel(document.document_type)} · {document.status} · {document.state}</span>
            <span className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-300">
              <span>{formatMoney(document.amount, document.currency)}</span>
              <span>{document.term || 'Term not found'}</span>
              {document.deadline && <span>Due {formatDate(document.deadline)}</span>}
              {document.required_credits !== null && <span>{document.required_credits} credits</span>}
            </span>
          </span>
        </div>
        {document.extraction_error && <span className="mt-2 block pl-[52px] text-xs text-rose-300">{document.extraction_error}</span>}
      </button>
      <div className="flex flex-wrap justify-end gap-2">
        <button type="button" className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800" onClick={() => onPreview(document)}>Preview PDF</button>
        {document.state === 'active' && document.status === 'extracted' && <button type="button" className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800" onClick={() => onEdit(document)}>Correct fields</button>}
        {document.state === 'active' && <button type="button" disabled={busy} className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200 disabled:opacity-50" onClick={() => onAction('archive', document)}>Archive</button>}
        {document.state !== 'active' && <button type="button" disabled={busy} className="rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200 disabled:opacity-50" onClick={() => onAction('restore', document)}>Restore</button>}
        {document.state !== 'deleted'
          ? <button type="button" disabled={busy} className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200 disabled:opacity-50" onClick={() => onAction('delete', document)}>Move to deleted</button>
          : <button type="button" disabled={busy} className="rounded-lg border border-rose-500/30 px-3 py-2 text-xs text-rose-200 disabled:opacity-50" onClick={() => onAction('permanent-delete', document)}>Delete permanently</button>}
      </div>
    </article>
  )
}

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [session, setSession] = useState(null)
  const [authLoading, setAuthLoading] = useState(Boolean(supabase))
  const [documents, setDocuments] = useState({ active: [], archived: [], deleted: [] })
  const [findings, setFindings] = useState([])
  const [selectedState, setSelectedState] = useState('active')
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [pdfPreview, setPdfPreview] = useState({ documentId: '', url: '' })
  const [editingDocument, setEditingDocument] = useState(null)
  const [report, setReport] = useState(null)
  const [insights, setInsights] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [busyDocumentId, setBusyDocumentId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [selectedFiles, setSelectedFiles] = useState([])
  const [uploadTypes, setUploadTypes] = useState({})
  const [correction, setCorrection] = useState(null)

  useEffect(() => {
    if (!supabase) return undefined
    let active = true
    supabase.auth.getSession()
      .then(({ data, error: sessionError }) => {
        if (!active) return
        if (sessionError) setError(`Unable to restore your session: ${sessionError.message}`)
        setSession(data.session)
        setAuthLoading(false)
      })
      .catch((cause) => {
        if (active) {
          setError(errorText(cause, 'Unable to restore your session.'))
          setAuthLoading(false)
        }
      })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setAuthLoading(false)
      if (!nextSession) {
        setDocuments({ active: [], archived: [], deleted: [] })
        setFindings([])
      }
    })
    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  const reloadData = useCallback(async () => {
    try {
      const data = await fetchUserData()
      setError('')
      setDocuments({ active: data.active, archived: data.archived, deleted: data.deleted })
      setFindings(data.currentFindings)
      return data
    } catch (cause) {
      setError(errorText(cause, 'Could not load your financial documents.'))
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (authLoading || authConfigurationIncomplete || remoteApiWithoutAuth || (supabase && !session)) return undefined
    let active = true
    fetchUserData()
      .then((data) => {
        if (!active) return
        setDocuments({ active: data.active, archived: data.archived, deleted: data.deleted })
        setFindings(data.currentFindings)
        setError('')
      })
      .catch((cause) => {
        if (active) setError(errorText(cause, 'Could not load your financial documents.'))
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [authLoading, session])

  useEffect(() => {
    if (!selectedDocument) return undefined
    let active = true
    let objectUrl = ''
    getDocumentPdf(selectedDocument.id)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setPdfPreview({ documentId: selectedDocument.id, url: objectUrl })
      })
      .catch((cause) => setError(errorText(cause, 'Unable to load this document preview.')))
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [selectedDocument])

  const visibleDocuments = documents[selectedState]
  const activeExtracted = documents.active.filter((document) => document.status === 'extracted')
  const totals = useMemo(() => {
    const tuitionDocuments = documents.active.filter((document) => document.document_type === 'tuition_bill' && document.amount !== null)
    const awardDocuments = documents.active.filter((document) => document.document_type === 'award_letter' && document.amount !== null)
    return {
      tuitionDocuments,
      awardDocuments,
      tuition: tuitionDocuments.reduce((total, document) => total + Number(document.amount), 0),
      awards: awardDocuments.reduce((total, document) => total + Number(document.amount), 0),
      deadlines: activeExtracted.filter((document) => document.deadline)
        .sort((left, right) => left.deadline.localeCompare(right.deadline)),
    }
  }, [activeExtracted, documents.active])

  function handleFilesAdded(files) {
    const pdfFiles = files.filter((file) => file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf'))
    setSelectedFiles((current) => [...current, ...pdfFiles.map((file) => ({ id: crypto.randomUUID(), file }))])
    if (pdfFiles.length !== files.length) setError('Only PDF documents are supported.')
    else setError('')
  }

  function openDocumentPreview(document) {
    setPdfPreview({ documentId: document.id, url: '' })
    setSelectedDocument(document)
  }

  function inferDocumentType(filename) {
    const normalized = filename.toLowerCase()
    if (normalized.includes('tuition') || normalized.includes('bill') || normalized.includes('invoice')) return 'tuition_bill'
    if (normalized.includes('abroad') || normalized.includes('program') || normalized.includes('quote')) return 'study_abroad_quote'
    if (normalized.includes('scholarship') || normalized.includes('award')) return 'award_letter'
    return ''
  }

  async function uploadSelectedFiles() {
    if (!selectedFiles.length) {
      setError('Choose at least one PDF to upload.')
      return
    }
    if (selectedFiles.some((item) => !(uploadTypes[item.id] || inferDocumentType(item.file.name)))) {
      setError('Choose a supported document type for each PDF before uploading.')
      return
    }
    setBusy(true)
    setError('')
    setNotice('')
    const results = []
    const failures = []
    for (const item of selectedFiles) {
      const { file } = item
      try {
        const result = await uploadDocument(file, uploadTypes[item.id] || inferDocumentType(file.name))
        results.push(result)
        if (result.status === 'failed') failures.push(`${file.name}: ${result.extraction_error || 'Text extraction failed.'}`)
      } catch (cause) {
        failures.push(`${file.name}: ${errorText(cause, 'Upload failed.')}`)
      }
    }
    setSelectedFiles([])
    setUploadTypes({})
    const refreshedData = await reloadData()
    const extracted = refreshedData?.active.filter((document) => document.status === 'extracted') || []
    if (extracted.length >= 2) {
      try {
        const nextReport = await createValidation(extracted.map((document) => document.id))
        const nextInsights = await createInsights(nextReport.id)
        setReport(nextReport)
        setInsights(nextInsights)
        setActivePage('Financial Insights')
      } catch (cause) {
        failures.push(errorText(cause, 'Documents uploaded, but the comparison could not be completed.'))
      }
    }
    if (results.length) setNotice(`${results.length} document${results.length === 1 ? '' : 's'} uploaded.`)
    if (failures.length) setError(failures.join(' '))
    setBusy(false)
  }

  async function runCheck() {
    if (activeExtracted.length < 2) {
      setError('At least two active documents with readable text are required to run a check.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const nextReport = await createValidation(activeExtracted.map((document) => document.id))
      const nextInsights = await createInsights(nextReport.id)
      setReport(nextReport)
      setInsights(nextInsights)
    } catch (cause) {
      setError(errorText(cause, 'Unable to run a financial document check.'))
    } finally {
      setBusy(false)
    }
  }

  async function refreshFromChatRecheck(reportId) {
    const nextReport = await getValidation(reportId)
    const nextInsights = await createInsights(nextReport.id)
    setReport(nextReport)
    setInsights(nextInsights)
    await reloadData()
  }

  async function handleDocumentAction(action, document) {
    setBusyDocumentId(document.id)
    setError('')
    try {
      if (action === 'permanent-delete') {
        if (!window.confirm(`Permanently delete ${document.filename} and its stored PDF? This cannot be undone.`)) return
        await permanentlyDeleteDocument(document.id)
      } else if (action === 'archive') {
        await archiveDocument(document.id)
      } else if (action === 'restore') {
        await restoreDocument(document.id)
      } else {
        await softDeleteDocument(document.id)
      }
      await reloadData()
      setNotice(action === 'permanent-delete' ? 'Document and PDF permanently deleted.' : `Document ${action === 'delete' ? 'moved to deleted' : `${action}d`}.`)
    } catch (cause) {
      setError(errorText(cause, 'Could not update this document.'))
    } finally {
      setBusyDocumentId('')
    }
  }

  function beginCorrection(document) {
    setEditingDocument(document)
    setCorrection({
      amount: document.amount === null ? '' : String(document.amount),
      term: document.term || '',
      deadline: document.deadline || '',
      required_credits: document.required_credits === null ? '' : String(document.required_credits),
      document_type: document.document_type,
    })
  }

  async function saveCorrection(event) {
    event.preventDefault()
    if (!editingDocument || !correction) return
    setBusy(true)
    setError('')
    try {
      await correctDocument(editingDocument.id, {
        amount: correction.amount === '' ? null : Number(correction.amount),
        term: correction.term || null,
        deadline: correction.deadline || null,
        required_credits: correction.required_credits === '' ? null : Number(correction.required_credits),
        document_type: correction.document_type,
      })
      await reloadData()
      setEditingDocument(null)
      setCorrection(null)
      setNotice('Corrected fields saved. Run a new check to refresh your findings.')
    } catch (cause) {
      setError(errorText(cause, 'Could not save the corrected fields.'))
    } finally {
      setBusy(false)
    }
  }

  async function signOut() {
    if (!supabase) return
    const { error: signOutError } = await supabase.auth.signOut()
    if (signOutError) setError(`Unable to sign out: ${signOutError.message}`)
    else {
      setReport(null)
      setInsights(null)
      setNotice('')
    }
  }

  function renderDashboard() {
    const nextDeadlines = totals.deadlines.slice(0, 3)
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Your money, in context</p><h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">Student finance overview</h2><p className="mt-2 text-sm text-slate-500">Based on your active, extracted documents.</p></div>
          <button type="button" onClick={() => setActivePage('Documents')} className="rounded-xl bg-[#111821] px-4 py-3 text-sm font-semibold text-white">Upload documents</button>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-4">
          <StatCard title="Tuition amounts" value={totals.tuitionDocuments.length ? formatMoney(totals.tuition) : '—'} change={`${totals.tuitionDocuments.length} docs`} detail="Extracted active tuition bills" tone="amber" tooltip="Sum of extracted amounts in active tuition-bill documents." />
          <StatCard title="Award amounts" value={totals.awardDocuments.length ? formatMoney(totals.awards) : '—'} change={`${totals.awardDocuments.length} docs`} detail="Extracted active award letters" tone="emerald" tooltip="Sum of extracted amounts in active award letters." />
          <StatCard title="Open findings" value={String(findings.length)} change="Current" detail="Computed from active extracted documents" tone="cyan" tooltip="Live validation findings; not a saved report." />
          <StatCard title="Documents checked" value={`${activeExtracted.length}`} change={`${documents.active.length} active`} detail="Successfully extracted documents" tone="violet" tooltip="Uploaded documents with extraction status 'extracted'." />
        </div>
        <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <SectionCard title="Current document findings" subtitle="Computed on read from active extracted documents" action={<button className="text-xs text-slate-300 underline" type="button" onClick={() => setActivePage('Financial Insights')}>Open insights</button>}>
            {findings.length ? <div className="space-y-3">{findings.slice(0, 4).map((finding) => (
              <article key={finding.id} className="rounded-xl border border-slate-800 bg-[#0f141a] p-4">
                <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-medium text-white">{finding.title}</h3><span className="rounded-full bg-slate-800 px-2.5 py-1 text-[10px] uppercase tracking-wider text-slate-300">{finding.severity}</span></div>
                <p className="mt-2 text-sm leading-6 text-slate-300">{finding.explanation}</p>
                <p className="mt-2 text-xs text-slate-400">Next step: {finding.suggested_action}</p>
              </article>
            ))}</div> : <p className="text-sm leading-6 text-slate-400">{activeExtracted.length < 2 ? 'Add at least two readable active PDFs to compare them.' : 'No inconsistencies were detected in the available fields.'}</p>}
          </SectionCard>
          <SectionCard title="Document dates" subtitle="Dates extracted from your active documents">
            {nextDeadlines.length ? <div className="space-y-3">{nextDeadlines.map((document) => (
              <div key={document.id} className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-[#0f141a] p-4">
                <div className="min-w-0"><p className="truncate text-sm font-medium text-white">{document.filename}</p><p className="mt-1 text-xs text-slate-400">{typeLabel(document.document_type)}</p></div>
                <div className="shrink-0 text-right"><p className="text-sm text-slate-200">{formatDate(document.deadline)}</p><p className="mt-1 text-xs text-slate-400">{formatMoney(document.amount, document.currency)}</p></div>
              </div>
            ))}</div> : <p className="text-sm text-slate-400">No deadlines were extracted from active documents.</p>}
          </SectionCard>
        </div>
      </div>
    )
  }

  function renderDocuments() {
    return (
      <div className="space-y-6">
        <div><p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Private document library</p><h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">Documents</h2><p className="mt-2 text-sm text-slate-500">Upload, correct, compare, archive, or delete your financial PDFs.</p></div>
        <SectionCard title="Add financial PDFs" subtitle="Files are stored privately and extracted by the backend">
          <DocumentDropzone onFilesAdded={handleFilesAdded} />
          {selectedFiles.length > 0 && <div className="mt-4 space-y-2">
            {selectedFiles.map(({ id, file }) => <div key={id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-800 bg-[#0f141a] p-3">
              <div className="min-w-0"><p className="truncate text-sm text-white">{file.name}</p><p className="text-xs text-slate-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p></div>
              <select aria-label={`Document type for ${file.name}`} className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-white" value={uploadTypes[id] ?? inferDocumentType(file.name)} onChange={(event) => setUploadTypes((current) => ({ ...current, [id]: event.target.value }))}>
                <option value="">Choose document type</option>
                {documentTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <button type="button" className="text-sm text-slate-400 hover:text-white" onClick={() => setSelectedFiles((current) => current.filter((selected) => selected.id !== id))} aria-label={`Remove ${file.name} from upload list`}>Remove</button>
            </div>)}
            <button type="button" disabled={busy} onClick={() => void uploadSelectedFiles()} className="rounded-xl bg-white px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? 'Uploading and checking…' : 'Upload and compare'}</button>
          </div>}
        </SectionCard>
        <SectionCard title="Your files" subtitle="Document records and lifecycle state">
          <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Filter by document state">
            {states.map((state) => <button key={state} type="button" onClick={() => setSelectedState(state)} aria-pressed={selectedState === state} className={`rounded-full border px-3 py-1.5 text-xs capitalize ${selectedState === state ? 'border-white bg-white text-slate-950' : 'border-slate-700 text-slate-300'}`}>{state} ({documents[state].length})</button>)}
          </div>
          {loading ? <p className="text-sm text-slate-400" role="status">Loading documents…</p>
            : visibleDocuments.length ? <div className="space-y-3">{visibleDocuments.map((document) => <DocumentRow key={document.id} document={document} busy={busyDocumentId === document.id} onAction={handleDocumentAction} onPreview={openDocumentPreview} onEdit={beginCorrection} />)}</div>
              : <p className="text-sm text-slate-400">No {selectedState} documents yet.</p>}
        </SectionCard>
      </div>
    )
  }

  function renderFinancialInsights() {
    return (
      <div className="space-y-6">
        <div className="flex flex-wrap items-end justify-between gap-4"><div><p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Validated documents</p><h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">Financial insights</h2><p className="mt-2 text-sm text-slate-500">Every report is based on a persisted validation run.</p></div><button type="button" onClick={() => void runCheck()} disabled={busy || activeExtracted.length < 2} className="rounded-xl bg-[#111821] px-4 py-3 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'Checking…' : 'Run checks again'}</button></div>
        {!report && <SectionCard title="No saved report in this session" subtitle="The backend can create a validation report and student-oriented insight summary from active documents">
          <p className="text-sm leading-6 text-slate-400">{activeExtracted.length < 2 ? 'Upload at least two active PDFs with readable text before running a comparison.' : 'Run checks to create a report and recommendations from your active documents.'}</p>
        </SectionCard>}
        {report && <>
          <SectionCard title={report.summary} subtitle={`Saved run · ${new Date(report.created_at).toLocaleString()}`}>
            <div className="grid gap-3 md:grid-cols-2">{report.documents.map((document) => <div key={document.id} className="rounded-xl border border-slate-800 bg-[#0f141a] p-4"><p className="truncate font-medium text-white">{document.filename}</p><p className="mt-2 text-xs text-slate-400">{typeLabel(document.document_type)} · {document.term || 'Term not found'} · {formatMoney(document.amount, document.currency)}</p></div>)}</div>
          </SectionCard>
          <SectionCard title="Findings to review" subtitle="Potential inconsistencies; confirm details with your school or provider">
            {report.findings.length ? <div className="space-y-3">{report.findings.map((finding) => <article key={finding.id} className="rounded-xl border border-slate-800 bg-[#0f141a] p-4"><div className="flex flex-wrap items-center justify-between gap-2"><h3 className="font-semibold text-white">{finding.title}</h3><span className="rounded-full bg-slate-800 px-2.5 py-1 text-[10px] uppercase text-slate-300">{finding.severity}</span></div><p className="mt-2 text-sm leading-6 text-slate-300">{finding.explanation}</p><p className="mt-2 text-xs text-slate-400">Suggested action: {finding.suggested_action}</p></article>)}</div>
              : <p className="text-sm text-slate-400">No potential inconsistencies were detected in the extracted fields.</p>}
          </SectionCard>
          {insights && <SectionCard title={insights.headline} subtitle="Your next move">
            <ul className="space-y-2">{insights.recommendations.map((item) => <li key={item} className="rounded-xl border border-slate-800 bg-[#0f141a] p-3 text-sm text-slate-200">{item}</li>)}</ul>
            <p className="mt-4 text-xs leading-5 text-slate-500">{insights.disclaimer}</p>
          </SectionCard>}
        </>}
      </div>
    )
  }

  function renderOtherPages() {
    if (activePage === 'AI Chat') {
      return (
        <div className="space-y-5">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Ask about your finances</p>
            <h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">AI financial assistant</h2>
            <p className="mt-2 text-sm text-slate-500">Get document-grounded answers, prepare corrections, or request a fresh validation.</p>
          </div>
          <FinancialChat
            onDocumentsChanged={reloadData}
            onRecheck={refreshFromChatRecheck}
          />
        </div>
      )
    }
    return <SectionCard title="Account settings" subtitle="Supabase authentication and account status">
      <div className="rounded-xl border border-slate-800 bg-[#0f141a] p-4"><p className="text-xs uppercase tracking-wider text-slate-400">Signed in as</p><p className="mt-2 text-white">{session?.user?.email || 'Local development identity'}</p></div>
      <p className="mt-4 text-sm leading-6 text-slate-400">The backend does not yet provide profile read or update endpoints. Name and university preferences are tracked in the API gap list.</p>
      {session && <button type="button" onClick={() => void signOut()} className="mt-5 rounded-xl border border-slate-700 px-4 py-2 text-sm text-white">Sign out</button>}
    </SectionCard>
  }

  const pageContent = activePage === 'Dashboard'
    ? renderDashboard()
    : activePage === 'Documents'
      ? renderDocuments()
      : activePage === 'Financial Insights'
        ? renderFinancialInsights()
        : renderOtherPages()

  if (authLoading) return <main className="grid min-h-screen place-items-center bg-[#080b0f] text-slate-300">Checking your secure session…</main>

  return (
    <div className="min-h-screen bg-[#f6f5f1] text-[#1b2430] xl:flex">
      <Sidebar activePage={activePage} onChange={setActivePage} aidSnapshot={totals.awardDocuments.length ? formatMoney(totals.awards) : '—'} />
      <main className="min-w-0 flex-1 p-4 sm:p-7 xl:p-9">
        <div className="mx-auto max-w-[1500px]">
          <header className="mb-7 flex flex-wrap items-center justify-between gap-4">
            <div><p className="text-xs uppercase tracking-[0.2em] text-slate-500">EduCash · Student finance</p><p className="mt-1 text-sm text-slate-600">{session?.user?.email || 'Local demo'}</p></div>
            <div className="flex items-center gap-3">
              {!supabase && <span className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-600">Local demo mode</span>}
              {session && <button type="button" onClick={() => void signOut()} className="rounded-xl border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700">Sign out</button>}
            </div>
          </header>
          {(authConfigurationIncomplete || remoteApiWithoutAuth) && <p className="mb-5 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900" role="alert">Set both VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to authenticate with the configured backend.</p>}
          {error && <div className="mb-5 flex items-start justify-between gap-3 rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900" role="alert"><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
          {notice && <p className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900" role="status">{notice}</p>}
          {authConfigurationIncomplete || remoteApiWithoutAuth
            ? <SectionCard title="Frontend configuration needed" subtitle="The remote backend requires a Supabase access token">
              <p className="text-sm leading-6 text-slate-400">Configure the frontend Supabase URL and anon key in the Vercel environment, then redeploy. Do not put the backend service key in frontend settings.</p>
            </SectionCard>
            : supabase && !session
            ? <AuthPanel />
            : pageContent}
          <footer className="mt-10 border-t border-slate-300 pt-4 text-xs text-slate-500">For planning support only—not financial advice. Confirm amounts, deadlines, and eligibility with your school or provider.</footer>
        </div>
      </main>
      {selectedDocument && <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-3 sm:p-8" role="dialog" aria-modal="true" aria-label={`Preview ${selectedDocument.filename}`}>
        <div className="flex h-full max-h-[900px] w-full max-w-5xl flex-col overflow-hidden rounded-2xl border border-slate-700 bg-[#0b0e12]">
          <div className="flex items-center justify-between gap-4 border-b border-slate-800 p-4"><div className="min-w-0"><p className="truncate font-medium text-white">{selectedDocument.filename}</p><p className="text-xs text-slate-400">{typeLabel(selectedDocument.document_type)}</p></div><button type="button" onClick={() => setSelectedDocument(null)} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-white">Close</button></div>
          {pdfPreview.documentId === selectedDocument.id && pdfPreview.url ? <iframe title={`PDF preview: ${selectedDocument.filename}`} src={pdfPreview.url} className="min-h-0 flex-1 bg-white" /> : <div className="grid flex-1 place-items-center text-sm text-slate-400">Loading private PDF…</div>}
        </div>
      </div>}
      {editingDocument && correction && <div className="fixed inset-0 z-[110] grid place-items-center bg-black/70 p-4" role="dialog" aria-modal="true" aria-label={`Correct ${editingDocument.filename}`}>
        <form onSubmit={saveCorrection} className="w-full max-w-xl space-y-4 rounded-2xl border border-slate-700 bg-[#0b0e12] p-6">
          <div className="flex items-start justify-between gap-4"><div><p className="text-xs uppercase tracking-wider text-slate-400">Correct extracted fields</p><h2 className="mt-2 text-lg font-semibold text-white">{editingDocument.filename}</h2></div><button type="button" onClick={() => setEditingDocument(null)} className="text-slate-300" aria-label="Close correction form">×</button></div>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-xs text-slate-300">Document type<select className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-white" value={correction.document_type} onChange={(event) => setCorrection({ ...correction, document_type: event.target.value })}>{documentTypes.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <label className="text-xs text-slate-300">Amount<input type="number" min="0" step="0.01" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-white" value={correction.amount} onChange={(event) => setCorrection({ ...correction, amount: event.target.value })} /></label>
            <label className="text-xs text-slate-300">Academic term<input className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-white" value={correction.term} onChange={(event) => setCorrection({ ...correction, term: event.target.value })} /></label>
            <label className="text-xs text-slate-300">Deadline<input type="date" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-white" value={correction.deadline} onChange={(event) => setCorrection({ ...correction, deadline: event.target.value })} /></label>
            <label className="text-xs text-slate-300">Required credits<input type="number" min="0" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-white" value={correction.required_credits} onChange={(event) => setCorrection({ ...correction, required_credits: event.target.value })} /></label>
          </div>
          <button type="submit" disabled={busy} className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">{busy ? 'Saving…' : 'Save correction'}</button>
        </form>
      </div>}
    </div>
  )
}

export default App
