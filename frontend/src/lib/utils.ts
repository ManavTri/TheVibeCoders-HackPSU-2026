import type { DocumentType } from '../types/api'

export const documentTypeLabels: Record<DocumentType, string> = {
  award_letter: 'Award letter',
  tuition_bill: 'Tuition bill',
  financial_aid_package: 'Financial aid package',
  study_abroad_quote: 'Study-abroad quote',
  loan_offer: 'Loan offer',
  payment_plan: 'Payment plan',
  housing_contract: 'Housing contract',
  other: 'Other financial document',
}

export function formatMoney(amount: string | number | null, currency = 'USD'): string {
  if (amount === null) return 'Not found'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 2 }).format(Number(amount))
}

export function formatDate(value: string | null): string {
  if (!value) return 'Not found'
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(
    new Date(`${value}T00:00:00Z`),
  )
}
