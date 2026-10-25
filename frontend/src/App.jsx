import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { StatCard } from './components/StatCard'
import { SectionCard } from './components/SectionCard'
import { DocumentDropzone } from './components/DocumentDropzone'
import {
  aiMessages,
  dashboardStats,
  deadlines,
  documentList,
  expenseCategories,
  financialTrends,
  scholarshipBreakdown,
  warnings,
} from './data/mockData'

const statusColors = {
  urgent: 'bg-neutral-800 text-neutral-100 ring-1 ring-neutral-600',
  watch: 'bg-neutral-800 text-neutral-100 ring-1 ring-neutral-600',
  normal: 'bg-neutral-800 text-neutral-100 ring-1 ring-neutral-600',
}

function escapePdfText(text) {
  return String(text)
    .replace(/\\/g, '\\\\')
    .replace(/\(/g, '\\(')
    .replace(/\)/g, '\\)')
    .slice(0, 120)
}

function createPdfBlobForDocument(documentName, summary) {
  const title = documentName || 'EduCash Document'
  const previewText = summary || 'Financial document preview'
  const escapedTitle = escapePdfText(title)
  const escapedSummary = escapePdfText(previewText)

  const content = `BT /F1 18 Tf 54 760 Td (${escapedTitle}) Tj 0 -30 Td /F1 12 Tf (${escapedSummary}) Tj ET`
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${content.length} >>\nstream\n${content}\nendstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ]

  let pdf = '%PDF-1.4\n'
  const offsets = [0]

  objects.forEach((objectContent, index) => {
    offsets.push(pdf.length)
    pdf += `${index + 1} 0 obj\n${objectContent}\nendobj\n`
  })

  const xrefOffset = pdf.length
  pdf += `xref\n0 ${objects.length + 1}\n`
  pdf += '0000000000 65535 f \n'

  offsets.slice(1).forEach((offset) => {
    pdf += `${String(offset).padStart(10, '0')} 00000 n \n`
  })

  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`

  return new Blob([pdf], { type: 'application/pdf' })
}

const documentAnalysisMap = {
  '2025 FAFSA Verification.pdf': {
    summary:
      'This document confirms the student’s dependency status and current aid eligibility. It aligns closely with the tuition invoice and scholarship renewal timeline.',
    important: [
      'Expected family contribution (EFC): $8,240',
      'Parent income verification is complete and filed.',
      'Aid package is likely to remain stable through the next semester.',
    ],
    related: ['Spring_2026_Tuition_Invoice.pdf', 'Scholarship_renewal_form.docx'],
    relationships: [
      'Matches the financial aid package for the current academic year.',
      'Linked to the remaining balance calculation shown on the dashboard.',
      'Cross-checks with the bank statement for household cash flow records.',
    ],
  },
  'Spring_2026_Tuition_Invoice.pdf': {
    summary:
      'This invoice outlines the student’s semester charges, due dates, and installment plan. It is the primary source of current billing obligations.',
    important: [
      'Total tuition due: $18,420',
      'Payment plan deadline: 4 days remaining.',
      'Two installments already covered by the scholarship award.',
    ],
    related: ['2025 FAFSA Verification.pdf', 'Scholarship_renewal_form.docx'],
    relationships: [
      'Directly corresponds to the tuition amount listed in the dashboard.',
      'Links to the school’s billing cycle and upcoming deadline alerts.',
      'Competes with household spending categories in the monthly budget view.',
    ],
  },
  'Scholarship_renewal_form.docx': {
    summary:
      'This form is required to maintain the merit scholarship award and should be signed before the Friday deadline to avoid interruption in funding.',
    important: [
      'Scholarship renewal is due in 14 days.',
      'Maintaining GPA above 3.7 is required for continued eligibility.',
      'Current award covers 42% of annual support.',
    ],
    related: ['2025 FAFSA Verification.pdf', 'Spring_2026_Tuition_Invoice.pdf'],
    relationships: [
      'Strengthens the aid package shown in the dashboard breakdown.',
      'Works with the FAFSA file to confirm continued need-based support.',
      'Offsets future tuition installment risk when submitted on time.',
    ],
  },
  'Bank_statement_July.pdf': {
    summary:
      'This bank statement reflects current household cash reserves and demonstrates available emergency funding for upcoming semester costs.',
    important: [
      'Current balance: $2,340 available emergency reserve.',
      'Recurring transfers match budgeted housing and food allocations.',
      'One large deposit is tied to scholarship disbursement timing.',
    ],
    related: ['Spring_2026_Tuition_Invoice.pdf', 'Scholarship_renewal_form.docx'],
    relationships: [
      'Supports the emergency fund value shown in the dashboard.',
      'Confirms the budget mix used in the financial insight chart.',
      'Helps validate the risk level tied to the remaining balance.',
    ],
  },
}

const documentWarnings = [
  {
    names: ['2025 FAFSA Verification.pdf', 'Spring_2026_Tuition_Invoice.pdf'],
    reason: 'Aid eligibility and tuition obligations are directly linked. The LLM detected a mismatch between expected aid coverage and the remaining installment cost.',
    severity: 'critical',
  },
  {
    names: ['Spring_2026_Tuition_Invoice.pdf', 'Scholarship_renewal_form.docx'],
    reason: 'Funding logic suggests the scholarship renewal could offset the payment gap if submitted before the Friday deadline.',
    severity: 'warning',
  },
  {
    names: ['2025 FAFSA Verification.pdf', 'Bank_statement_July.pdf'],
    reason: 'Cash-flow records and aid documents should align to confirm the household emergency reserve remains sufficient for the semester.',
    severity: 'info',
  },
]

const severityStyles = {
  critical: 'bg-[#d9857c]/15 text-[#f1b0a7] ring-1 ring-[#d9857c]/40',
  warning: 'bg-[#e7b66b]/15 text-[#f2d39c] ring-1 ring-[#e7b66b]/40',
  info: 'bg-[#83a99b]/15 text-[#c2d9d0] ring-1 ring-[#83a99b]/40',
}

const documentFilterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Aid', value: 'aid' },
  { label: 'Tuition', value: 'tuition' },
  { label: 'Scholarship', value: 'scholarship' },
  { label: 'Budget', value: 'budget' },
]

const totalSemesterCost = 36170
const currentTuitionDue = 18420
const confirmedAidAmount = 9750
const remainingBalanceAmount = currentTuitionDue - confirmedAidAmount
const fundingVerificationSources = { confirmed: 3, total: 4 }

function InfoTooltip({ label, text, children }) {
  return (
    <div className="group relative z-[60] inline-flex">
      <div className="transition duration-150 ease-out group-hover:brightness-110">{children}</div>
      <div className="pointer-events-none absolute left-1/2 top-full z-[90] mt-2 w-52 -translate-x-1/2 rounded-xl border border-slate-200 bg-[#fffefc] px-2.5 py-2 text-left text-[11px] leading-5 text-slate-800 opacity-0 shadow-lg shadow-slate-900/10 transition-all duration-150 ease-out group-hover:opacity-100 group-focus-within:opacity-100">
        <p className="font-semibold">{label}</p>
        <p className="mt-0.5 text-[10px] text-slate-500">{text}</p>
      </div>
    </div>
  )
}

function App() {
  const [activePage, setActivePage] = useState('Dashboard')
  const [documents, setDocuments] = useState(documentList)
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [expandedRows, setExpandedRows] = useState({})
  const [galleryMode, setGalleryMode] = useState(false)
  const [archivedIds, setArchivedIds] = useState([])
  const [comparisonFocus, setComparisonFocus] = useState([])
  const [archivedDocuments, setArchivedDocuments] = useState([])
  const [deletedDocuments, setDeletedDocuments] = useState([])
  const [recentUploadsFilter, setRecentUploadsFilter] = useState('all')
  const [hoveredMonth, setHoveredMonth] = useState('Apr')
  const [selectedWarning, setSelectedWarning] = useState(null)
  const [toast, setToast] = useState(null)
  const [undoStack, setUndoStack] = useState([])
  const [redoStack, setRedoStack] = useState([])
  const [selectedDeadline, setSelectedDeadline] = useState('Tuition installment')
  const [financialComparison, setFinancialComparison] = useState([
    '2025 FAFSA Verification.pdf',
    'Spring_2026_Tuition_Invoice.pdf',
  ])
  const [hoveredWarningCard, setHoveredWarningCard] = useState(null)
  const [hoveredBudgetCategory, setHoveredBudgetCategory] = useState(null)
  const [hoveredAidCategory, setHoveredAidCategory] = useState(null)
  const [aiDraft, setAiDraft] = useState('')
  const [settings, setSettings] = useState(() => {
    const saved = typeof window !== 'undefined' ? window.localStorage.getItem('educash-settings') : null

    if (!saved) {
      return {
        theme: 'dark',
        profile: {
          firstName: 'Alex',
          lastName: 'Rivera',
          email: 'alex.rivera@northbridge.edu',
          major: 'Business Analytics',
          academicYear: '2025-2026',
        },
        financialPreferences: {
          monthlyBudget: 6150,
          emergencyBuffer: 15,
        },
        notifications: {
          emailReminders: true,
          smsAlerts: true,
          resetAlerts: true,
        },
        privacy: {
          dataSync: true,
          usageAnalytics: false,
          retainAccountHistory: true,
        },
      }
    }

    try {
      return { ...{
        theme: 'dark',
        profile: {
          firstName: 'Alex',
          lastName: 'Rivera',
          email: 'alex.rivera@northbridge.edu',
          major: 'Business Analytics',
          academicYear: '2025-2026',
        },
        financialPreferences: {
          monthlyBudget: 6150,
          emergencyBuffer: 15,
        },
        notifications: {
          emailReminders: true,
          smsAlerts: true,
          resetAlerts: true,
        },
        privacy: {
          dataSync: true,
          usageAnalytics: false,
          retainAccountHistory: true,
        },
      }, ...JSON.parse(saved) }
    } catch (error) {
      return {
        theme: 'dark',
        profile: {
          firstName: 'Alex',
          lastName: 'Rivera',
          email: 'alex.rivera@northbridge.edu',
          major: 'Business Analytics',
          academicYear: '2025-2026',
        },
        financialPreferences: {
          monthlyBudget: 6150,
          emergencyBuffer: 15,
        },
        notifications: {
          emailReminders: true,
          smsAlerts: true,
          resetAlerts: true,
        },
        privacy: {
          dataSync: true,
          usageAnalytics: false,
          retainAccountHistory: true,
        },
      }
    }
  })
  const aiInputRef = useRef(null)
  const aiButtonRef = useRef(null)

  const monthlyBudget = Number(settings.financialPreferences.monthlyBudget) || 6150

  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('educash-settings', JSON.stringify(settings))
    }
  }, [settings])

  useEffect(() => {
    const root = document.body
    root.dataset.theme = settings.theme
    root.style.background = settings.theme === 'light' ? '#f4f2ee' : '#0b1017'
  }, [settings.theme])

  const deadlineDetails = {
    'Tuition installment': {
      title: 'Payment plan window',
      summary: 'This installment covers the next tuition bill and is the largest short-term obligation still outstanding before the semester closes out.',
      details: ['Due in 4 days', 'Next payment due: $4,200', 'Review the tuition invoice to confirm the school withdrawal date before the final installment triggers a late fee.'],
      related: ['Spring_2026_Tuition_Invoice.pdf', 'Bank_statement_July.pdf'],
    },
    'Housing payment': {
      title: 'Housing cash requirement',
      summary: 'This payment keeps the lease active and is bundled with the remaining monthly budget for living costs.',
      details: ['Due in 9 days', 'Next payment due: $1,350', 'Alignment with the monthly budget shows this is within the current household cash-flow plan.'],
      related: ['Bank_statement_July.pdf', '2025 FAFSA Verification.pdf'],
    },
    'Scholarship renewal': {
      title: 'Renewal requirement',
      summary: 'This form maintains the merit scholarship and should be submitted before the Friday cutoff to avoid interrupted support.',
      details: ['Due in 14 days', 'Required form must be signed and submitted before Friday', 'Missing the deadline may reduce the funded portion of the upcoming term.'],
      related: ['Scholarship_renewal_form.docx', '2025 FAFSA Verification.pdf'],
    },
  }

  const hasUploadedDocuments = documents.length > 0

  const addDocuments = (uploadedFiles) => {
    const newDocs = uploadedFiles.map((file, index) => ({
      id: `${file.name}-${file.size}-${index}`,
      name: file.name,
      type: 'Uploaded',
      updated: 'Just now',
      status: 'Uploaded',
    }))

    setDocuments((currentDocuments) => [...newDocs, ...currentDocuments])
  }

  const getDocumentAnalysis = (document) => {
    if (!document) return null
    return (
      documentAnalysisMap[document.name] || {
        summary:
          'This document is ready for review. The LLM layer can compare it against related records once the backend is connected.',
        important: [
          'File is flagged for a final verification review.',
          'No urgent issues were detected from the current mock dataset.',
        ],
        related: ['2025 FAFSA Verification.pdf', 'Spring_2026_Tuition_Invoice.pdf'],
        relationships: [
          'This file is connected to the current billing and aid workflow.',
          'It should be reviewed alongside the financial summary for consistency.',
        ],
      }
    )
  }

  const toggleRow = (documentId) => {
    setExpandedRows((current) => ({
      ...current,
      [documentId]: !current[documentId],
    }))
  }

  const removeDocument = (documentId) => {
    const targetDocument = documents.find((document) => document.id === documentId)
    if (!targetDocument) return

    const action = {
      kind: 'delete',
      document: { ...targetDocument },
      previousStatus: targetDocument.status,
    }

    setDocuments((currentDocuments) => currentDocuments.filter((document) => document.id !== documentId))
    setDeletedDocuments((current) => [...current, { ...targetDocument, removedAt: new Date().toISOString() }])
    setUndoStack((current) => [...current, action])
    setRedoStack([])
    setToast({ kind: 'deleted', document: targetDocument, previousStatus: targetDocument.status })
  }

  const archiveDocument = (documentId) => {
    const targetDocument = documents.find((document) => document.id === documentId)
    if (!targetDocument) return

    const action = {
      kind: 'archive',
      document: { ...targetDocument },
      previousStatus: targetDocument.status,
    }

    setArchivedIds((current) => current.includes(documentId) ? current : [...current, documentId])
    setDocuments((currentDocuments) => currentDocuments.filter((document) => document.id !== documentId))
    setArchivedDocuments((current) => [...current, { ...targetDocument, archivedAt: new Date().toISOString() }])
    setUndoStack((current) => [...current, action])
    setRedoStack([])
    setToast({ kind: 'archived', document: targetDocument, previousStatus: targetDocument.status })
  }

  const undoDocumentAction = (actionOverride) => {
    const action = actionOverride || undoStack[undoStack.length - 1]
    if (!action) return

    setUndoStack((current) => current.filter((entry) => entry !== action))
    setRedoStack((current) => [...current, action])

    if (action.kind === 'archive') {
      setArchivedDocuments((current) => current.filter((item) => item.id !== action.document.id))
      setArchivedIds((current) => current.filter((id) => id !== action.document.id))
      setDocuments((current) => [{ ...action.document, status: action.previousStatus, updated: 'Restored' }, ...current])
    }

    if (action.kind === 'delete') {
      setDeletedDocuments((current) => current.filter((item) => item.id !== action.document.id))
      setDocuments((current) => [{ ...action.document, status: action.previousStatus, updated: 'Restored' }, ...current])
    }

    setToast(null)
  }

  const redoDocumentAction = () => {
    const action = redoStack[redoStack.length - 1]
    if (!action) return

    setRedoStack((current) => current.filter((entry) => entry !== action))
    setUndoStack((current) => [...current, action])

    if (action.kind === 'archive') {
      setDocuments((current) => current.filter((document) => document.id !== action.document.id))
      setArchivedIds((current) => current.includes(action.document.id) ? current : [...current, action.document.id])
      setArchivedDocuments((current) => [...current, { ...action.document, archivedAt: new Date().toISOString() }])
    }

    if (action.kind === 'delete') {
      setDocuments((current) => current.filter((document) => document.id !== action.document.id))
      setDeletedDocuments((current) => [...current, { ...action.document, removedAt: new Date().toISOString() }])
    }
  }

  const restoreDocument = (document, kind) => {
    const action = {
      kind,
      document: { ...document },
      previousStatus: document.status,
    }
    undoDocumentAction(action)
  }

  const openDocumentPreview = (documentName) => {
    const targetDocument = documents.find((document) => document.name === documentName)

    if (!targetDocument) return

    setSelectedWarning(null)
    setActivePage('Documents')
    setSelectedDocument(targetDocument)
  }

  const handleWarningClick = (warning) => {
    setSelectedWarning(warning)
  }

  const visibleDocuments = useMemo(() => {
    const activeDocuments = documents.filter((document) => !archivedIds.includes(document.id))

    if (recentUploadsFilter === 'all') {
      return activeDocuments
    }

    const mapping = {
      aid: 'Financial aid',
      tuition: 'Tuition',
      scholarship: 'Scholarship',
      budget: 'Budget',
    }

    return activeDocuments.filter((document) => document.type === mapping[recentUploadsFilter])
  }, [archivedIds, documents, recentUploadsFilter])

  const compareTargets = useMemo(() => {
    const matches = financialComparison
      .map((name) => documents.find((document) => document.name === name))
      .filter(Boolean)

    if (matches.length >= 2) return matches.slice(0, 2)

    const fallback = documents.slice(0, 2)
    return fallback
  }, [documents, financialComparison])

  const triggerWarningFlow = (warning) => {
    setActivePage('Documents')
    setGalleryMode(false)
    setRecentUploadsFilter('all')
    setFinancialComparison(warning.names)

    window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'auto' })
      const section = document.getElementById('document-warning-section')
      const card = document.querySelector(`[data-warning-key="${warning.names.join('|')}"]`)

      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' })
        section.classList.remove('outline-flash')
        void section.offsetWidth
        section.classList.add('outline-flash')
      }

      window.setTimeout(() => {
        if (card) {
          card.classList.remove('card-flash')
          void card.offsetWidth
          card.classList.add('card-flash')
        }
      }, 700)

      window.setTimeout(() => {
        setSelectedWarning(warning)
      }, 1400)
    }, 300)
  }

  const triggerDocumentsComparisonFlow = (warning) => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    setActivePage('Documents')
    setGalleryMode(false)
    setRecentUploadsFilter('all')
    setFinancialComparison(warning.names)

    window.setTimeout(() => {
      const section = document.getElementById('document-warning-section')
      const card = document.querySelector(`[data-warning-key="${warning.names.join('|')}"]`)

      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' })
        section.classList.remove('outline-flash')
        void section.offsetWidth
        section.classList.add('outline-flash')
      }

      window.setTimeout(() => {
        if (card) {
          card.classList.remove('card-flash')
          void card.offsetWidth
          card.classList.add('card-flash')
        }
      }, 700)

      window.setTimeout(() => {
        setSelectedWarning(warning)
      }, 1350)
    }, 450)
  }

  const triggerAiPromptFlow = (warning) => {
    const prompt = `Review the ${warning.names.join(' and ')} documents and tell me the most important next action for ${warning.reason.toLowerCase()}.`

    setAiDraft(prompt)
    window.scrollTo({ top: 0, behavior: 'auto' })
    setActivePage('AI Chat')

    window.setTimeout(() => {
      const input = aiInputRef.current || document.getElementById('ai-chat-input')
      if (input) {
        input.focus()
        input.value = prompt
        input.dispatchEvent(new Event('input', { bubbles: true }))
      }

      const button = aiButtonRef.current || document.getElementById('ai-send-button')
      if (button) {
        button.classList.remove('ring-2', 'ring-white', 'ring-offset-2')
        void button.offsetWidth
        button.classList.add('ring-2', 'ring-white', 'ring-offset-2')
      }
    }, 500)
  }

  const comparisonMetrics = useMemo(() => {
    if (compareTargets.length < 2) {
      return []
    }

    const [left, right] = compareTargets
    const leftAnalysis = getDocumentAnalysis(left)
    const rightAnalysis = getDocumentAnalysis(right)

    return [
      {
        label: 'Tuition / aid',
        left: leftAnalysis.important[0],
        right: rightAnalysis.important[0],
        difference: leftAnalysis.important[0] !== rightAnalysis.important[0],
      },
      {
        label: 'Due date alignment',
        left: leftAnalysis.relationships[1],
        right: rightAnalysis.relationships[1],
        difference: leftAnalysis.relationships[1] !== rightAnalysis.relationships[1],
      },
      {
        label: 'Cash flow impact',
        left: leftAnalysis.relationships[2],
        right: rightAnalysis.relationships[2],
        difference: leftAnalysis.relationships[2] !== rightAnalysis.relationships[2],
      },
      {
        label: 'Money consistency',
        left: left.status,
        right: right.status,
        difference: left.status !== right.status,
      },
    ]
  }, [compareTargets])

  const previewPdfUrl = useMemo(() => {
    if (!selectedDocument) return null

    const analysis = getDocumentAnalysis(selectedDocument)
    const blob = createPdfBlobForDocument(selectedDocument.name, analysis.summary)

    return URL.createObjectURL(blob)
  }, [selectedDocument])

  useEffect(() => {
    if (!toast) return undefined

    const timeoutId = window.setTimeout(() => {
      setToast(null)
    }, 4000)

    return () => window.clearTimeout(timeoutId)
  }, [toast])

  useEffect(() => {
    const handleKeyDown = (event) => {
      const isModifier = event.ctrlKey || event.metaKey
      const targetTag = event.target && event.target.tagName ? event.target.tagName.toLowerCase() : ''

      if (event.key === 'Escape') {
        if (selectedDocument) {
          setSelectedDocument(null)
        } else if (selectedWarning) {
          setSelectedWarning(null)
        }
      }

      if (targetTag === 'input' || targetTag === 'textarea') {
        return
      }

      if (isModifier && !event.shiftKey && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        undoDocumentAction()
      }

      if (isModifier && event.shiftKey && event.key.toLowerCase() === 'z') {
        event.preventDefault()
        redoDocumentAction()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [undoStack, redoStack, selectedDocument, selectedWarning])

  useEffect(() => {
    return () => {
      if (previewPdfUrl) {
        URL.revokeObjectURL(previewPdfUrl)
      }
    }
  }, [previewPdfUrl])

  const renderPage = () => {
    if (activePage === 'Dashboard') {
      return (
        <div className="space-y-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Financial overview</p>
              <h2 className="mt-2 text-3xl font-semibold text-[#1b2430] md:text-4xl">Semester payment dashboard</h2>
            </div>
            <button
              type="button"
              className="rounded-full border border-neutral-700 bg-white px-5 py-2.5 text-sm font-semibold text-black shadow-sm transition-transform hover:-translate-y-0.5 hover:brightness-110"
            >
              Review next payment
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <StatCard
              title="Total semester cost"
              value={`$${totalSemesterCost.toLocaleString()}`}
              change=" "
              detail="Projected full cost"
              tone="amber"
              tooltip="This is the total cost for the semester, including tuition and associated charges."
            />
            <StatCard
              title="Confirmed aid"
              value={`$${confirmedAidAmount.toLocaleString()}`}
              change="Verified"
              detail="Document-confirmed"
              tone="emerald"
              tooltip="Confirmed aid is based on documents already submitted and verified."
            />
            <StatCard
              title="Remaining balance"
              value={`$${remainingBalanceAmount.toLocaleString()}`}
              change="Current due"
              detail="After confirmed aid"
              tone="cyan"
              tooltip="This is the amount still owed after confirmed aid is applied to the current tuition due."
            />
          </div>

          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-3xl border border-[#d5b07e]/40 bg-[#111821] p-5 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.02)] xl:max-w-[520px] xl:self-start">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[11px] uppercase tracking-[0.22em] text-[#d8c4a3]">Action required</p>
                <span className="rounded-full border border-[#d5b07e]/40 bg-[#d5b07e]/10 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.18em] text-[#f0d7a7]">Priority</span>
              </div>
              <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                  <h3 className="text-2xl font-semibold text-white">Submit the scholarship renewal form</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-300">This is the most urgent item preventing a smoother payment plan for the upcoming installment. It also supports a stronger aid position if submitted before the deadline.</p>
                </div>
                <div className="rounded-2xl border border-[#d5b07e]/30 bg-[#1a2029] px-4 py-3 text-right md:min-w-[150px]">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Current due</p>
                  <p className="mt-2 text-3xl font-semibold text-white">$18,420</p>
                </div>
              </div>
            </div>

            <SectionCard title="Upcoming deadlines" subtitle="Payments and required actions">
              <div className="space-y-3">
                {deadlines.map((item) => {
                  const detail = deadlineDetails[item.name]
                  const isOpen = selectedDeadline === item.name

                  return (
                    <div key={item.name} className="rounded-2xl border border-slate-800 bg-slate-950/40 p-4 transition-all duration-150 hover:-translate-y-0.5 hover:brightness-110">
                      <button
                        type="button"
                        className="w-full text-left"
                        onClick={() => setSelectedDeadline(isOpen ? null : item.name)}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-white">{item.name}</p>
                            <p className="mt-1 text-sm text-slate-400">{item.due}</p>
                          </div>
                          <span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.16em] ${statusColors[item.status]}`}>
                            {item.status}
                          </span>
                        </div>
                        <p className="mt-3 text-lg font-semibold text-neutral-200">{item.amount}</p>
                      </button>

                      {isOpen && detail ? (
                        <div className="deadline-panel relative mt-3 rounded-2xl border border-slate-700 bg-[#fffefc] p-3 text-[#1f2a33] shadow-lg shadow-slate-900/10">
                          <div className="absolute -top-2 left-6 h-4 w-4 rotate-45 border-l border-t border-slate-700 bg-[#fffefc]" />
                          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Deadline context</p>
                          <p className="mt-2 text-sm font-semibold text-slate-900">{detail.title}</p>
                          <p className="mt-1 text-sm leading-5 text-slate-600">{detail.summary}</p>
                          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs leading-5 text-slate-600">
                            {detail.details.map((line) => (
                              <li key={line}>{line}</li>
                            ))}
                          </ul>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {detail.related.map((doc) => (
                              <button
                                key={doc}
                                type="button"
                                className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-1 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-700 transition hover:brightness-110"
                                onClick={() => setSelectedDocument({ name: doc })}
                              >
                                {doc}
                              </button>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  )
                })}
              </div>
            </SectionCard>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="rounded-3xl border border-[#1c2730] bg-[#0d1219] p-6 text-white shadow-inner shadow-black/20">
              <div className="mb-6 flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-[30px] font-semibold tracking-[-0.06em] text-white">Aid source breakdown</h3>
                  <p className="mt-1 text-lg text-slate-400">How your $9,750 in financial aid is distributed</p>
                </div>
                <div className="text-right">
                  <p className="text-[28px] font-semibold tracking-[-0.05em] text-white">$9,750</p>
                  <p className="mt-1 text-[10px] uppercase tracking-[0.22em] text-slate-400">Total</p>
                </div>
              </div>

              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-5">
                  {scholarshipBreakdown.map((item, index) => {
                    const isActive = hoveredAidCategory === item.label
                    const colorClass =
                      index === 0 ? 'bg-[#9bb7a9]' : index === 1 ? 'bg-[#b7c9d9]' : index === 2 ? 'bg-[#e0c381]' : 'bg-[#d9d7d0]'

                    return (
                      <button
                        key={item.label}
                        type="button"
                        onMouseEnter={() => setHoveredAidCategory(item.label)}
                        onMouseLeave={() => setHoveredAidCategory(null)}
                        className={`w-full rounded-2xl p-3 text-left transition-all duration-200 ${
                          isActive ? 'border border-slate-600 bg-white/[0.02]' : 'border border-transparent'
                        } ${hoveredAidCategory && !isActive ? 'opacity-45' : 'opacity-100'}`}
                      >
                        <div className="flex items-center gap-3 text-xl font-medium text-white">
                          <InfoTooltip label={item.label} text={`${item.label} represents ${item.value}% of the total confirmed aid.`}>
                            <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full border border-white/30 text-sm font-semibold text-white ${colorClass}`}>
                              ?
                            </span>
                          </InfoTooltip>
                          <span className="sr-only">{item.label}</span>
                        </div>
                        <div className="mt-4 text-4xl font-semibold tracking-[-0.06em] text-white">{item.amount}</div>
                        <div className="mt-1 text-lg text-slate-400">{item.value}% of total</div>
                      </button>
                    )
                  })}
                </div>

                <div className="h-3 w-full overflow-hidden rounded-full bg-[#e8ecef] shadow-[inset_0_0_0_1px_rgba(15,23,42,0.04)]">
                  <div className="flex h-full w-full overflow-hidden rounded-full">
                    {scholarshipBreakdown.map((item, index) => {
                      const isActive = hoveredAidCategory === item.label
                      const colorClass =
                        index === 0 ? 'bg-[#9bb7a9]' : index === 1 ? 'bg-[#b7c9d9]' : index === 2 ? 'bg-[#e0c381]' : 'bg-[#d9d7d0]'

                      return (
                        <button
                          key={`${item.label}-bar`}
                          type="button"
                          onMouseEnter={() => setHoveredAidCategory(item.label)}
                          onMouseLeave={() => setHoveredAidCategory(null)}
                          className={`h-full border-r-2 border-[#0d1219] transition-all duration-200 ${colorClass} shadow-[0_4px_0_rgba(15,23,42,0.12)] ${
                            isActive ? 'brightness-100' : hoveredAidCategory ? 'opacity-30 saturate-50' : 'opacity-100'
                          }`}
                          style={{ width: `${item.value}%` }}
                          aria-label={`Highlight ${item.label}`}
                        />
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            <SectionCard title="Financial warnings" subtitle="Items to review this week">
              <div className="space-y-3">
                {!hasUploadedDocuments ? (
                  <div className="rounded-2xl border border-dashed border-slate-600 bg-slate-950/30 p-5 text-center">
                    <p className="text-lg font-medium text-white">No documents uploaded yet</p>
                    <p className="mt-2 text-sm text-slate-400">Upload your first document to unlock comparisons and insights.</p>
                    <button
                      type="button"
                      onClick={() => setActivePage('Documents')}
                      className="mt-4 rounded-full border border-slate-600 bg-[#f5f5f1] px-4 py-2 text-sm font-semibold text-[#0d1219] transition hover:brightness-110"
                    >
                      Upload documents
                    </button>
                  </div>
                ) : (
                  warnings.map((warning) => {
                    const isHovered = hoveredWarningCard === warning.title

                    return (
                      <button
                        key={warning.title}
                        type="button"
                        onMouseEnter={() => setHoveredWarningCard(warning.title)}
                        onMouseLeave={() => setHoveredWarningCard(null)}
                        onClick={() => triggerAiPromptFlow(warning)}
                        className={`group relative w-full overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-left transition-all duration-200 ${
                          isHovered ? 'scale-[1.01] border-slate-600' : ''
                        } ${hoveredWarningCard && !isHovered ? 'opacity-50 blur-[0.2px]' : ''}`}
                      >
                        {isHovered ? (
                          <div
                            className="absolute inset-0 z-10 flex cursor-pointer items-center justify-center bg-[#0d141b]/70 backdrop-blur-[1px]"
                            onClick={(event) => {
                              event.stopPropagation()
                              triggerAiPromptFlow(warning)
                            }}
                          >
                            <span className="rounded-full border border-white/30 bg-[#f5f5f1] px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-[#0d1219]">
                              What next?
                            </span>
                          </div>
                        ) : null}

                        <div className="relative z-0 flex items-center justify-between gap-3">
                          <p className="font-medium text-white">{warning.title}</p>
                          <span
                            className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${
                              warning.severity === 'high'
                                ? 'bg-neutral-800 text-neutral-100'
                                : warning.severity === 'medium'
                                  ? 'bg-neutral-800 text-neutral-100'
                                  : 'bg-neutral-800 text-neutral-100'
                            }`}
                          >
                            {warning.severity}
                          </span>
                        </div>
                        <p className="relative z-0 mt-2 text-sm text-slate-400">{warning.text}</p>
                      </button>
                    )
                  })
                )}
              </div>
            </SectionCard>
          </div>
        </div>
      )
    }

    if (activePage === 'Documents') {
      return (
        <div className="space-y-6">
          <div className="rounded-2xl border border-[#dfe4da] bg-[#f4f3f0] p-4 shadow-sm">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <p className="text-[11px] uppercase tracking-[0.22em] text-[#5f6b76]">Required files</p>
                <h2 className="mt-1 text-2xl font-semibold text-[#1b2430]">Document center</h2>
              </div>
              <button type="button" className="rounded-xl border border-[#d0d5d4] bg-[#171d24] px-4 py-2 text-sm font-medium text-[#f5f7fa] transition-transform hover:-translate-y-0.5 hover:brightness-110">
                Export summary
              </button>
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-center gap-3 sm:gap-5">
              {[
                { label: 'Documents', sub: 'Select scholarship and tuition documents', icon: '▣' },
                { label: 'Compare Documents', sub: 'Find differences, overlaps, and conflicts', icon: '⇄' },
                { label: 'Financial Insights', sub: 'Understand risks and recommended next steps', icon: '▤' },
              ].map((step, index) => (
                <>
                  <div key={step.label} className="flex items-center gap-3 text-[#1b2430]">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#d4d9d2] bg-[#eef1ee] text-base text-[#1b2430]">
                      {step.icon}
                    </div>
                    <div className="min-w-0 text-left">
                      <p className="text-sm font-semibold text-[#1b2430]">{step.label}</p>
                      <p className="mt-0.5 text-[11px] leading-tight text-[#5d6874]">{step.sub}</p>
                    </div>
                  </div>
                  {index < 2 ? (
                    <div key={`${step.label}-arrow`} className="hidden text-lg text-[#4f5964] sm:block">→</div>
                  ) : null}
                </>
              ))}
            </div>

            <div className="mt-5 rounded-2xl border border-[#dfe4da] bg-[#f7f6f3] p-3">
              <div className="mt-4">
                <DocumentDropzone onFilesAdded={addDocuments} />
              </div>
            </div>
          </div>

          <SectionCard title="Recent uploads" subtitle="Filtered by file type and financial significance">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap gap-2">
                {documentFilterOptions.map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => setRecentUploadsFilter(option.value)}
                    className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                      recentUploadsFilter === option.value
                        ? 'border-[#1b2430] bg-[#1b2430] text-white'
                        : 'border-[#dfe4da] bg-[#f6f5f1] text-[#3a4652]'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <button
                type="button"
                onClick={() => setGalleryMode((current) => !current)}
                className="rounded-full border border-[#dfe4da] bg-[#f6f5f1] px-3 py-1.5 text-xs font-medium text-[#1b2430] transition-all hover:-translate-y-0.5 hover:bg-white"
              >
                {galleryMode ? 'List view' : 'Gallery view'}
              </button>
            </div>

            <div className="transition-all duration-200 ease-out">
            {galleryMode ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3 transition-all duration-200 ease-out">
                {visibleDocuments.map((document) => {
                  const analysis = getDocumentAnalysis(document)

                  return (
                    <div
                      key={document.id}
                      className="rounded-2xl border border-slate-800 bg-[#0f1318] p-3 transition-colors hover:border-slate-600"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedDocument(document)}
                          className="rounded-lg border border-neutral-600 bg-[#131a20] px-2 py-1 text-[11px] text-white"
                        >
                          Preview
                        </button>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => archiveDocument(document.id)}
                            className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200"
                          >
                            Archive
                          </button>
                          <button
                            type="button"
                            onClick={() => removeDocument(document.id)}
                            className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
                          >
                            Delete
                          </button>
                        </div>
                      </div>

                      <div className="mt-3 rounded-xl border border-slate-800 bg-[#121821] p-3">
                        <div className="rounded-lg border border-slate-700 bg-[#f4f0ec] p-2 text-left">
                          <div className="mb-2 rounded-md border border-slate-300 bg-white p-2">
                            <div className="mb-2 flex items-center justify-between text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                              <span>{document.name.replace(/\.[^.]+$/, '').slice(0, 18)}</span>
                              <span className="rounded bg-slate-200 px-1 py-0.5 text-[8px] text-slate-700">PDF</span>
                            </div>
                            <div className="space-y-1.5">
                              <div className="h-2 w-full rounded bg-slate-200" />
                              <div className="h-2 w-4/5 rounded bg-slate-200" />
                              <div className="h-2 w-3/5 rounded bg-slate-200" />
                              <p className="mt-2 text-[9px] leading-4 text-slate-600">{analysis.summary.slice(0, 70)}...</p>
                            </div>
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium text-white">{document.name}</p>
                          <p className="mt-1 text-xs text-slate-400">{document.type}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => toggleRow(document.id)}
                          className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200"
                        >
                          {expandedRows[document.id] ? 'Hide' : 'Open'}
                        </button>
                      </div>

                      <p className="mt-3 text-xs text-slate-400">{document.updated}</p>
                      <p className="mt-3 text-sm leading-6 text-slate-300">{analysis.summary.slice(0, 90)}...</p>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="overflow-hidden rounded-2xl border border-slate-800 transition-all duration-200 ease-out">
                <table className="min-w-full divide-y divide-slate-800 text-left text-sm">
                  <thead className="bg-slate-950/70 text-slate-300">
                    <tr>
                      <th className="px-4 py-3 font-medium">Name</th>
                      <th className="px-4 py-3 font-medium">Type</th>
                      <th className="px-4 py-3 font-medium">Updated</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                      <th className="px-4 py-3 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-900/40 text-slate-200">
                    {visibleDocuments.map((document) => {
                      const expanded = !!expandedRows[document.id]
                      const analysis = getDocumentAnalysis(document)

                      return (
                        <Fragment key={document.id}>
                          <tr
                            onClick={() => setSelectedDocument(document)}
                            className="cursor-pointer transition-colors hover:bg-slate-800/60"
                          >
                            <td className="px-4 py-3 font-medium text-white">
                              <div className="flex items-center gap-3">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    toggleRow(document.id)
                                  }}
                                  className="flex h-6 w-6 items-center justify-center rounded-full border border-slate-700 bg-slate-950 text-xs text-slate-300"
                                  aria-label={`Toggle preview for ${document.name}`}
                                >
                                  {expanded ? '▾' : '▸'}
                                </button>
                                {document.name}
                              </div>
                            </td>
                            <td className="px-4 py-3">{document.type}</td>
                            <td className="px-4 py-3 text-slate-400">{document.updated}</td>
                            <td className="px-4 py-3">
                              <span className="rounded-full bg-neutral-800 px-2 py-1 text-xs text-neutral-100">
                                {document.status}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <div className="flex justify-end gap-2">
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    archiveDocument(document.id)
                                  }}
                                  className="rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200"
                                >
                                  Archive
                                </button>
                                <button
                                  type="button"
                                  onClick={(event) => {
                                    event.stopPropagation()
                                    removeDocument(document.id)
                                  }}
                                  className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-[11px] text-rose-200"
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                          {expanded ? (
                            <tr key={`${document.id}-preview`} className="bg-slate-950/40">
                              <td colSpan="5" className="px-4 py-3">
                                <div className="rounded-xl border border-slate-800 bg-slate-900/70 p-3">
                                  <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Quick preview</p>
                                  <p className="mt-2 text-sm leading-6 text-slate-200">{analysis.summary.slice(0, 140)}...</p>
                                </div>
                              </td>
                            </tr>
                          ) : null}
                        </Fragment>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
            </div>
          </SectionCard>

          <SectionCard title="Document warnings" subtitle="AI-detected inconsistencies and review priorities" id="document-warning-section">
            <div className="grid gap-3 lg:grid-cols-3">
              {documentWarnings.map((warning) => (
                <div
                  key={warning.reason}
                  onClick={() => handleWarningClick(warning)}
                  className="cursor-pointer rounded-2xl border border-slate-800 bg-[#0f1318] p-4 transition-all duration-200 hover:brightness-110 hover:border-slate-600 hover:bg-[#111b23]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Detected issue</p>
                    <InfoTooltip
                      label="Issue category"
                      text={warning.severity === 'critical' ? 'Critical mismatch between funding and billing records.' : warning.severity === 'warning' ? 'Potential funding timing risk requiring attention.' : 'Informational mismatch to review for consistency.'}
                    >
                      <span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${severityStyles[warning.severity]}`}>
                        {warning.severity}
                      </span>
                    </InfoTooltip>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {warning.names.map((name) => (
                      <button
                        key={name}
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation()
                          openDocumentPreview(name)
                        }}
                        className="rounded-full border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-200 transition-colors hover:border-slate-500 hover:text-white"
                      >
                        {name}
                      </button>
                    ))}
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{warning.reason}</p>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard title="Archived and recently deleted" subtitle="Stored here and kept out of the main uploads list">
            <div className="grid gap-6 xl:grid-cols-2">
              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Archived</p>
                {archivedDocuments.length === 0 ? (
                  <p className="text-sm text-slate-400">No archived documents yet.</p>
                ) : (
                  archivedDocuments.map((document) => (
                    <div key={document.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
                      <div>
                        <p className="font-medium text-white">{document.name}</p>
                        <p className="text-xs text-slate-400">Archived {document.archivedAt ? 'recently' : 'manually'}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => restoreDocument(document, 'archived')}
                        className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                      >
                        Restore
                      </button>
                    </div>
                  ))
                )}
              </div>

              <div className="space-y-3">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Recently deleted</p>
                {deletedDocuments.length === 0 ? (
                  <p className="text-sm text-slate-400">No recently deleted documents.</p>
                ) : (
                  deletedDocuments.map((document) => (
                    <div key={document.id} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/40 p-3">
                      <div>
                        <p className="font-medium text-white">{document.name}</p>
                        <p className="text-xs text-slate-400">Auto-deletes after 30 days</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => restoreDocument(document, 'deleted')}
                        className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-200"
                      >
                        Restore
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </SectionCard>

        </div>
      )
    }

    if (activePage === 'Settings') {
      return (
        <div className="space-y-6">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Control center</p>
            <h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">Settings</h2>
          </div>

          <div className="grid gap-6 xl:grid-cols-2">
            <SectionCard title="Profile" subtitle="Account and academic details">
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">First name</span>
                    <input
                      value={settings.profile.firstName}
                      onChange={(event) => setSettings((current) => ({
                        ...current,
                        profile: { ...current.profile, firstName: event.target.value },
                      }))}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none ring-0 transition focus:border-slate-500"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Last name</span>
                    <input
                      value={settings.profile.lastName}
                      onChange={(event) => setSettings((current) => ({
                        ...current,
                        profile: { ...current.profile, lastName: event.target.value },
                      }))}
                      className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                    />
                  </label>
                </div>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Email</span>
                  <input
                    value={settings.profile.email}
                    onChange={(event) => setSettings((current) => ({
                      ...current,
                      profile: { ...current.profile, email: event.target.value },
                    }))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Major</span>
                  <input
                    value={settings.profile.major}
                    onChange={(event) => setSettings((current) => ({
                      ...current,
                      profile: { ...current.profile, major: event.target.value },
                    }))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Academic year</span>
                  <select
                    value={settings.profile.academicYear}
                    onChange={(event) => setSettings((current) => ({
                      ...current,
                      profile: { ...current.profile, academicYear: event.target.value },
                    }))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                  >
                    <option value="2025-2026">2025-2026</option>
                    <option value="2026-2027">2026-2027</option>
                    <option value="2027-2028">2027-2028</option>
                  </select>
                </label>
              </div>
            </SectionCard>

            <SectionCard title="Appearance" subtitle="Theme and interface preferences">
              <div className="space-y-4">
                <div className="flex gap-3">
                  {['dark', 'light'].map((theme) => (
                    <button
                      key={theme}
                      type="button"
                      onClick={() => setSettings((current) => ({ ...current, theme }))}
                      className={`flex-1 rounded-xl border px-3 py-2 text-sm font-medium transition ${
                        settings.theme === theme
                          ? 'border-[#7ea7d9] bg-[#111c26] text-white'
                          : 'border-slate-700 bg-slate-950/20 text-slate-300'
                      }`}
                    >
                      {theme === 'dark' ? 'Dark mode' : 'Light mode'}
                    </button>
                  ))}
                </div>

                <div className="rounded-2xl border border-slate-800 bg-slate-950/30 p-4">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Preview</p>
                  <div className="mt-3 flex items-center justify-between rounded-xl border border-slate-700 bg-slate-900/40 px-3 py-2 text-sm text-slate-200">
                    <span>Accent color</span>
                    <span className="h-3 w-3 rounded-full bg-[#9bc2d9]" />
                  </div>
                </div>
              </div>
            </SectionCard>

            <SectionCard title="Financial preferences" subtitle="Budget and academic settings">
              <div className="space-y-4">
                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Monthly budget</span>
                  <input
                    type="number"
                    min="0"
                    value={settings.financialPreferences.monthlyBudget}
                    onChange={(event) => setSettings((current) => ({
                      ...current,
                      financialPreferences: {
                        ...current.financialPreferences,
                        monthlyBudget: Number(event.target.value) || 0,
                      },
                    }))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 block text-xs uppercase tracking-[0.2em] text-slate-400">Emergency buffer %</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={settings.financialPreferences.emergencyBuffer}
                    onChange={(event) => setSettings((current) => ({
                      ...current,
                      financialPreferences: {
                        ...current.financialPreferences,
                        emergencyBuffer: Number(event.target.value) || 0,
                      },
                    }))}
                    className="w-full rounded-xl border border-slate-700 bg-slate-950/40 px-3 py-2.5 text-sm text-white outline-none transition focus:border-slate-500"
                  />
                </label>
              </div>
            </SectionCard>

            <SectionCard title="Notifications" subtitle="Alerts and reminders">
              <div className="space-y-3">
                {[
                  ['Email reminders', 'emailReminders'],
                  ['SMS payment alerts', 'smsAlerts'],
                  ['Deadline reset prompts', 'resetAlerts'],
                ].map(([label, key]) => (
                  <label key={key} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/30 px-4 py-3 text-sm text-slate-200">
                    <span>{label}</span>
                    <input
                      type="checkbox"
                      checked={settings.notifications[key]}
                      onChange={(event) => setSettings((current) => ({
                        ...current,
                        notifications: {
                          ...current.notifications,
                          [key]: event.target.checked,
                        },
                      }))}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-[#a6d6cd] focus:ring-slate-400"
                    />
                  </label>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Privacy & data" subtitle="Access controls and storage settings">
              <div className="space-y-3">
                {[
                  ['Sync documents securely', 'dataSync'],
                  ['Usage analytics sharing', 'usageAnalytics'],
                  ['Retain account history', 'retainAccountHistory'],
                ].map(([label, key]) => (
                  <label key={key} className="flex items-center justify-between gap-3 rounded-2xl border border-slate-800 bg-slate-950/30 px-4 py-3 text-sm text-slate-200">
                    <span>{label}</span>
                    <input
                      type="checkbox"
                      checked={settings.privacy[key]}
                      onChange={(event) => setSettings((current) => ({
                        ...current,
                        privacy: {
                          ...current.privacy,
                          [key]: event.target.checked,
                        },
                      }))}
                      className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-[#a6d6cd] focus:ring-slate-400"
                    />
                  </label>
                ))}
              </div>
            </SectionCard>
          </div>
        </div>
      )
    }

    if (activePage === 'Financial Insights') {
      return (
        <div className="space-y-6">
          <div>
            <p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Financial insights</p>
            <h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">Findings, comparison results, and outlook</h2>
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.5fr_0.8fr]">
            <SectionCard title="Findings and risks" subtitle="Detected issues ranked by urgency">
              <div className="space-y-4">
                {documentWarnings.map((warning) => (
                  <div key={warning.reason} className="rounded-2xl border border-slate-800 bg-[#0f1318] p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-white">{warning.names.join(' + ')}</p>
                      <button
                        type="button"
                        onClick={() => triggerDocumentsComparisonFlow(warning)}
                        className="rounded-lg border border-neutral-600 bg-[#111821] px-3 py-1.5 text-xs text-white transition-transform hover:-translate-y-0.5 hover:brightness-110"
                      >
                        View docs
                      </button>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                      <InfoTooltip
                        label="Issue category"
                        text={warning.severity === 'critical' ? 'Critical mismatch between funding and billing records.' : warning.severity === 'warning' ? 'Potential funding timing risk requiring attention.' : 'Informational mismatch to review for consistency.'}
                      >
                        <span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${severityStyles[warning.severity]}`}>
                          {warning.severity}
                        </span>
                      </InfoTooltip>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-slate-300">{warning.reason}</p>
                    <div className="mt-3 rounded-xl border border-slate-700 bg-[#121821] p-3">
                      <p className="text-[10px] uppercase tracking-[0.2em] text-slate-400">Recommended action</p>
                      <p className="mt-2 text-sm text-slate-200">Review the associated documents and submit any required form before the next payment date.</p>
                    </div>
                  </div>
                ))}
              </div>
            </SectionCard>

            <SectionCard title="Funding verification" subtitle="Confirmed document coverage">
              <div className="space-y-4">
                <div className="rounded-2xl border border-slate-800 bg-[#0f141a] p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">Verification status</p>
                  <p className="mt-3 text-4xl font-semibold text-white">{fundingVerificationSources.confirmed} of {fundingVerificationSources.total}</p>
                  <p className="mt-2 text-sm text-slate-300">Sources confirmed based on actual document verification results.</p>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-[#0f141a] p-4">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">Current due</p>
                  <p className="mt-3 text-3xl font-semibold text-white">$18,420</p>
                  <p className="mt-2 text-sm text-slate-300">This is the current amount due, distinct from the total semester cost of $36,170.</p>
                </div>
              </div>
            </SectionCard>
          </div>

          <SectionCard title="Document comparison results" subtitle="Side-by-side financial details and discrepancies">
            <div className="overflow-hidden rounded-2xl border border-slate-800">
              <table className="min-w-full text-left text-sm">
                <thead className="bg-[#111821] text-slate-300">
                  <tr>
                    <th className="px-4 py-3 font-medium">Comparison target</th>
                    <th className="px-4 py-3 font-medium">{compareTargets[0].name}</th>
                    <th className="px-4 py-3 font-medium">{compareTargets[1].name}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800 bg-[#0f1318] text-slate-200">
                  {comparisonMetrics.map((row) => (
                    <tr key={row.label} className={row.difference ? 'bg-[#151d26]' : ''}>
                      <td className="px-4 py-3 font-medium text-white">{row.label}</td>
                      <td className="px-4 py-3">{row.left}</td>
                      <td className="px-4 py-3">{row.right}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionCard>

          <SectionCard title="Financial outlook" subtitle="Funding versus expenses; verified documents are distinguished from estimates">
            <div className="flex flex-col gap-4">
              <div className="rounded-xl border border-slate-800 bg-[#0f141a] p-3 text-sm text-slate-300">
                <span className="font-medium text-white">Note:</span> This outlook combines verified document totals with user-provided estimates, so the forecast should be treated as directional rather than final.
              </div>

              <div className="flex items-center justify-end gap-4 text-[11px] uppercase tracking-[0.18em] text-slate-300">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm bg-[#83a99b]" />
                  Verified funding
                </div>
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-sm bg-[#a9c8dc]" />
                  Estimated expenses
                </div>
              </div>

              <div className="grid grid-cols-[38px_1fr] gap-3">
                <div className="flex h-52 flex-col justify-between pt-2 text-[10px] text-slate-400">
                  {[6000, 4000, 2000, 0].map((tick) => (
                    <span key={tick} className="text-right">${tick.toLocaleString()}</span>
                  ))}
                </div>

                <div className="relative h-52 overflow-visible">
                  <div className="absolute inset-0 grid grid-cols-6 gap-3 px-2 pb-2 pt-2">
                    {financialTrends.map((item) => {
                      const maxValue = 6000
                      const fundingHeight = (item.funding / maxValue) * 100
                      const expenseHeight = (item.expenses / maxValue) * 100
                      const isFocused = hoveredMonth === item.month
                      const shortfall = item.funding - item.expenses

                      return (
                        <div key={item.month} className="relative z-10 flex flex-1 items-end justify-center overflow-visible">
                          <div
                            className={`pointer-events-none absolute -top-16 left-1/2 z-[60] w-36 -translate-x-1/2 rounded-xl border border-[#dfe4da] bg-[#fffefc] px-2.5 py-2 text-[11px] text-[#1f2a33] shadow-lg shadow-slate-900/10 transition-all duration-150 ${
                              isFocused ? 'opacity-100' : 'opacity-0'
                            }`}
                            style={{ left: '50%', transform: 'translateX(-50%)' }}
                          >
                            <div className="font-semibold">{item.month}</div>
                            <div>Funding: ${item.funding.toLocaleString()}</div>
                            <div>Expenses: ${item.expenses.toLocaleString()}</div>
                            <div className={shortfall >= 0 ? 'text-[#83a99b]' : 'text-[#d9857c]'}>
                              {shortfall >= 0 ? 'Surplus' : 'Shortfall'}: ${Math.abs(shortfall).toLocaleString()}
                            </div>
                          </div>

                          <div
                            className={`relative z-10 flex h-full w-full items-end justify-center gap-2 transition-all duration-200 ${isFocused ? 'opacity-100' : 'opacity-70'}`}
                            onMouseEnter={() => setHoveredMonth(item.month)}
                            onMouseLeave={() => setHoveredMonth(null)}
                          >
                            <div
                              className="w-1/2 rounded-t-xl bg-[#83a99b] transition-all duration-200"
                              style={{ height: `${fundingHeight}%` }}
                            />
                            <div
                              className="w-1/2 rounded-t-xl bg-[#a9c8dc] transition-all duration-200"
                              style={{ height: `${expenseHeight}%` }}
                            />
                          </div>
                          <span className="absolute -bottom-6 text-[10px] text-slate-400">{item.month}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>
            </div>

            <div className="mt-5">
              <div className="rounded-2xl border border-slate-800 bg-[#0f1318] p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Budget allocation</p>
                <div className="mt-4 h-5 overflow-hidden rounded-full bg-[#edf0ee] shadow-[inset_0_0_0_1px_rgba(15,23,42,0.06)]">
                  <div className="flex h-full w-full overflow-hidden rounded-full">
                    {expenseCategories.map((item, index) => (
                      <div
                        key={`${item.label}-stack`}
                        className={`h-full border-r border-[#0e1418] ${
                          index === 0
                            ? 'bg-[#a7c5b3]'
                            : index === 1
                              ? 'bg-[#b7d0e5]'
                              : index === 2
                                ? 'bg-[#e0c58a]'
                                : 'bg-[#d8d3cf]'
                        }`}
                        style={{ width: `${item.value}%` }}
                      />
                    ))}
                  </div>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {expenseCategories.map((item) => (
                    <div key={item.label} className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#111821] px-3 py-2">
                      <div className="flex items-center gap-3">
                        <span className="h-3 w-3 rounded-full" style={{ backgroundColor: item.colorValue }} />
                        <span className="text-sm text-slate-200">{item.label}</span>
                      </div>
                      <span className="text-sm font-medium text-white">{item.value}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </SectionCard>
        </div>
      )
    }

    return (
      <div className="space-y-6">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-[#5f6b76]">Assistant</p>
          <h2 className="mt-2 text-3xl font-semibold text-[#1b2430]">AI financial guidance</h2>
        </div>

        <SectionCard title="Chat with EduCash AI" subtitle="Personalized advice for your student budget">
          <div className="space-y-4">
            {aiMessages.map((message) => (
              <div key={`${message.sender}-${message.time}`} className={`rounded-2xl p-4 ${message.sender === 'AI' ? 'bg-slate-950/60' : 'bg-neutral-800'}`}>
                <div className="mb-2 flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-white">{message.sender}</span>
                  <span className="text-xs text-slate-400">{message.time}</span>
                </div>
                <p className="text-sm leading-6 text-slate-200">{message.text}</p>
              </div>
            ))}
          </div>

          <div className="mt-6 rounded-2xl border border-slate-700 bg-slate-950/50 p-3">
            <textarea
              id="ai-chat-input"
              ref={aiInputRef}
              value={aiDraft}
              onChange={(event) => setAiDraft(event.target.value)}
              className="min-h-24 w-full resize-none rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm text-slate-100 outline-none placeholder:text-slate-500"
              placeholder="Ask about tuition deadlines, budget improvements, or aid strategy..."
            />
            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="flex gap-2">
                {['Tuition timing', 'Aid strategy', 'Budget plan'].map((tip) => (
                  <span key={tip} className="rounded-full border border-slate-700 px-2 py-1 text-xs text-slate-300">
                    {tip}
                  </span>
                ))}
              </div>
              <button type="button" className="rounded-full border border-neutral-600 bg-white px-4 py-2 text-sm font-semibold text-black">
                Send
              </button>
            </div>
          </div>
        </SectionCard>
      </div>
    )
  }

  const analysis = getDocumentAnalysis(selectedDocument)

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex max-w-[1600px] flex-col lg:flex-row">
        <Sidebar activePage={activePage} onChange={setActivePage} />

        <main className="flex-1 bg-[radial-gradient(circle_at_top,_rgba(107,164,126,0.08),transparent_35%),linear-gradient(180deg,#f7f5f1_0%,#f2f4ee_100%)] px-4 py-5 sm:px-6 lg:px-8 lg:py-6">
          <header className="mb-6 flex flex-col gap-3 border-b border-[#dfe4da] pb-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm text-[#53665f]">Welcome back, Alex</p>
              <h1 className="mt-1 text-2xl font-semibold text-[#1b2430]">Monday, October 24</h1>
            </div>
            <div className="flex items-center gap-3 self-start rounded-full border border-[#dfe4da] bg-[#f8f7f4] px-3 py-2 text-sm text-[#2a3c37] md:self-auto">
              <span className="h-2.5 w-2.5 rounded-full bg-[#83a99b]" />
              Account status: active
            </div>
          </header>

          {renderPage()}
        </main>
      </div>

      {selectedWarning ? (
        <div className="fixed inset-0 z-[70] bg-[#03080d]/90 backdrop-blur-sm">
          <div className="relative mx-auto mt-10 h-[calc(100vh-5rem)] w-[min(1200px,92vw)] overflow-hidden rounded-[28px] border border-slate-700 bg-[#0a1017] shadow-2xl shadow-black/50">
            <button
              type="button"
              onClick={() => setSelectedWarning(null)}
              aria-label="Close warning detail"
              className="absolute right-5 top-5 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-2xl leading-none text-slate-200"
            >
              ×
            </button>

            <div className="flex h-full flex-col xl:flex-row">
              <div className="flex-1 border-b border-slate-800 xl:border-b-0 xl:border-r xl:border-slate-800">
                <div className="flex h-full flex-col p-6">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Warning detail</p>
                      <h3 className="mt-1 text-2xl font-semibold text-white">{selectedWarning.names.join(' + ')}</h3>
                    </div>
                    <span className={`rounded-full px-2.5 py-1 text-[10px] uppercase tracking-[0.2em] ${severityStyles[selectedWarning.severity]}`}>
                      {selectedWarning.severity}
                    </span>
                  </div>

                  <div className="grid h-full min-h-0 gap-4 xl:grid-cols-2">
                    {selectedWarning.names.map((name) => {
                      const warningDocument = documents.find((document) => document.name === name)
                      const previewUrl = warningDocument ? (() => {
                        const analysis = getDocumentAnalysis(warningDocument)
                        const blob = createPdfBlobForDocument(warningDocument.name, analysis.summary)
                        return URL.createObjectURL(blob)
                      })() : null

                      return (
                        <div key={name} className="overflow-hidden rounded-[22px] border border-slate-800 bg-[#0d141b]">
                          <div className="flex items-center justify-between border-b border-slate-800 bg-[#111b25] px-4 py-3">
                            <span className="text-sm font-medium text-white">{name}</span>
                            <button
                              type="button"
                              onClick={() => openDocumentPreview(name)}
                              className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200"
                            >
                              Open document
                            </button>
                          </div>
                          <div className="h-[calc(100%-53px)] bg-[#101922] p-2">
                            {previewUrl ? (
                              <iframe
                                src={previewUrl}
                                title={name}
                                className="h-full w-full rounded-2xl border border-slate-700 bg-white"
                              />
                            ) : null}
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>

              <aside className="h-full w-full overflow-y-auto border-t border-slate-800 bg-[#040a12] p-5 xl:w-[420px] xl:border-t-0 xl:border-l">
                <div className="mb-5">
                  <p className="text-[11px] uppercase tracking-[0.22em] text-neutral-400">Issue category</p>
                  <h3 className="mt-1 text-xl font-semibold text-white">
                    {selectedWarning.severity === 'critical' ? 'Aid / billing conflict' : selectedWarning.severity === 'warning' ? 'Funding timing risk' : 'Cash-flow consistency'}
                  </h3>
                </div>

                <div className="space-y-4">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Why this matters</p>
                    <p className="mt-3 text-sm leading-7 text-slate-200">{selectedWarning.reason}</p>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Recommended next step</p>
                    <ul className="mt-3 space-y-3 text-sm text-slate-200">
                      <li>• Review the linked documents before the next payment date.</li>
                      <li>• Confirm funding amounts match the current tuition schedule.</li>
                      <li>• Update the file list if a revised document is available.</li>
                    </ul>
                  </div>

                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Related files</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {selectedWarning.names.map((name) => (
                        <button
                          key={name}
                          type="button"
                          onClick={() => openDocumentPreview(name)}
                          className="rounded-full border border-slate-700 bg-slate-950/40 px-2.5 py-1 text-xs text-slate-200 hover:border-slate-500"
                        >
                          {name}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </aside>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className="fixed bottom-5 right-5 z-[80] flex items-center gap-3 rounded-2xl border border-slate-700 bg-[#0d141b] px-4 py-3 shadow-2xl shadow-black/30">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">{toast.kind === 'archived' ? 'Archived' : 'Deleted'}</p>
            <p className="mt-1 text-sm text-white">{toast.document.name}</p>
          </div>
          <button
            type="button"
            onClick={() => restoreDocument(toast.document, toast.kind)}
            className="rounded-full border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-100"
          >
            Undo
          </button>
        </div>
      ) : null}

      {selectedDocument ? (
        <div className="fixed inset-0 z-[70] bg-[#03080d]/90 backdrop-blur-sm">
          <div className="relative h-full w-full">
            <div className="absolute left-6 top-5 z-10">
              <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">Document preview</p>
              <h3 className="mt-1 text-2xl font-semibold text-white">{selectedDocument.name}</h3>
            </div>

            <button
              type="button"
              onClick={() => setSelectedDocument(null)}
              aria-label="Close document preview"
              className="absolute right-6 top-5 z-10 flex h-10 w-10 items-center justify-center rounded-full border border-slate-700 bg-slate-900 text-2xl leading-none text-slate-200"
            >
              ×
            </button>

            <div className="flex h-full w-full flex-col pt-20 xl:flex-row">
              <div className="flex-1 border-b border-slate-800 xl:border-b-0 xl:border-r xl:border-slate-800">
                <div className="h-[calc(100vh-116px)] p-6">
                  <div className="h-full overflow-hidden rounded-[24px] border border-slate-800 bg-[#0d141b] shadow-2xl shadow-black/40">
                    <div className="flex items-center justify-between border-b border-slate-800 bg-[#111b25] px-5 py-3">
                      <div>
                        <p className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{selectedDocument.type}</p>
                        <p className="mt-1 text-lg font-medium text-white">{selectedDocument.name}</p>
                      </div>
                      <button
                        type="button"
                        className="rounded-full border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-200"
                      >
                        Open file
                      </button>
                    </div>

                    <div className="h-[calc(100%-60px)] bg-[#101922] p-2">
                      {previewPdfUrl ? (
                        <iframe
                          src={previewPdfUrl}
                          title={selectedDocument.name}
                          className="h-full w-full rounded-2xl border border-slate-700 bg-white"
                        />
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>

              <aside className="h-full w-full overflow-y-auto border-t border-slate-800 bg-[#040a12] p-5 xl:w-[420px] xl:border-t-0 xl:border-l">
                <div className="mb-5 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] uppercase tracking-[0.22em] text-neutral-400">Metadata & analysis</p>
                    <h3 className="mt-1 text-xl font-semibold text-white">AI document insights</h3>
                  </div>
                  <button
                    type="button"
                    className="rounded-full border border-neutral-600 bg-neutral-800 px-3 py-2 text-xs font-medium text-neutral-100"
                  >
                    Analyze now
                  </button>
                </div>

                <div className="space-y-3">
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Status</p>
                    <p className="mt-2 text-2xl font-semibold text-white">Complete</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Updated</p>
                    <p className="mt-2 text-2xl font-semibold text-white">2 hours ago</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Format</p>
                    <p className="mt-2 text-2xl font-semibold text-white">PDF</p>
                  </div>
                  <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                    <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Owner</p>
                    <p className="mt-2 text-2xl font-semibold text-white">Alex R.</p>
                  </div>
                </div>

                {analysis ? (
                  <div className="mt-5 space-y-4">
                    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Summary</p>
                      <p className="mt-3 text-sm leading-7 text-slate-200">{analysis.summary}</p>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Important information</p>
                      <ul className="mt-3 space-y-3 text-sm text-slate-200">
                        {analysis.important.map((item) => (
                          <li key={item} className="flex gap-2 leading-6">
                            <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-white" />
                            <span>{item}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-4">
                      <p className="text-[11px] uppercase tracking-[0.18em] text-slate-400">Related documents</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {analysis.related.map((item) => (
                          <span key={item} className="rounded-full border border-slate-700 bg-slate-950/40 px-2.5 py-1 text-xs text-slate-200">
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="mt-5 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 text-sm italic text-slate-300">
                  Example UI with fictional financial information.
                </div>
              </aside>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}

export default App
