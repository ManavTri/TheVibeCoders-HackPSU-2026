export type DocumentType =
  | 'award_letter'
  | 'tuition_bill'
  | 'financial_aid_package'
  | 'study_abroad_quote'
  | 'loan_offer'
  | 'payment_plan'
  | 'housing_contract'
  | 'other'
export type DocumentStatus = 'uploaded' | 'extracted' | 'failed'
export type Severity = 'error' | 'warning' | 'info'

export interface FinancialDocument {
  id: string
  filename: string
  document_type: DocumentType
  amount: string | number | null
  currency: string
  term: string | null
  deadline: string | null
  required_credits: number | null
  extraction_envelope?: Record<string, unknown> | null
  extracted_text?: string
}

export interface DocumentRecord extends FinancialDocument {
  status: DocumentStatus
  created_at: string
  extraction_error: string | null
  extraction_source?: 'gemini' | 'fallback' | null
  type_detected?: DocumentType | null
  type_confidence?: number | null
  needs_review?: boolean
  user_edited_fields?: string[]
}

export type DocumentSummary = Pick<
  FinancialDocument,
  'id' | 'filename' | 'document_type' | 'amount' | 'currency' | 'term' | 'deadline' | 'required_credits'
>

export interface Finding {
  id?: string
  rule_id: string
  severity: Severity
  title: string
  explanation: string
  document_ids: string[]
  fields: Record<string, string | number | null>
  suggested_action: string
}

export interface ValidationReport {
  id: string
  created_at: string
  documents: DocumentSummary[]
  findings: Finding[]
  summary: string
}

export interface CurrentFindingsReport {
  findings: Finding[]
  summary: {
    skipped_rules: number
    rule_errors: Array<{ rule_id: string; error_class: string }>
  }
}

export interface Insights {
  report_id: string
  headline: string
  recommendations: string[]
  disclaimer: string
}

export interface DocumentCorrection {
  amount?: number | null
  currency?: string
  term?: string | null
  deadline?: string | null
  required_credits?: number | null
  document_type?: DocumentType
}
