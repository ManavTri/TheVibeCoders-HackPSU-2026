export type DocumentType = 'award_letter' | 'tuition_bill' | 'study_abroad_quote'
export type Severity = 'high' | 'medium' | 'low'

export interface FinancialDocument {
  id: string
  filename: string
  document_type: DocumentType
  amount: string | number | null
  currency: string
  term: string | null
  deadline: string | null
  required_credits: number | null
  extracted_text?: string
}

export interface DocumentSummary extends Omit<FinancialDocument, 'extracted_text'> {}

export interface Finding {
  rule_id: string
  severity: Severity
  title: string
  message: string
  document_ids: string[]
  details: Record<string, string | number | null>
}

export interface ValidationReport {
  id: string
  created_at: string
  documents: DocumentSummary[]
  findings: Finding[]
  summary: string
}

export interface Insights {
  report_id: string
  headline: string
  recommendations: string[]
  disclaimer: string
}
