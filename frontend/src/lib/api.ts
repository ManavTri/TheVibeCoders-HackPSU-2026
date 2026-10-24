import type { DocumentType, FinancialDocument, Insights, ValidationReport } from '../types/api'

const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}/api${path}`, init)
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { detail?: string } | null
    throw new Error(body?.detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function extractDocuments(files: File[], documentTypes: DocumentType[]): Promise<FinancialDocument[]> {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  documentTypes.forEach((type) => body.append('document_types', type))
  return request<FinancialDocument[]>('/documents/extract', { method: 'POST', body })
}

export function createValidation(documents: FinancialDocument[]): Promise<ValidationReport> {
  return request<ValidationReport>('/validations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(documents),
  })
}

export function getReport(id: string): Promise<ValidationReport> {
  return request<ValidationReport>(`/validations/${encodeURIComponent(id)}`)
}

export function getInsights(id: string): Promise<Insights> {
  return request<Insights>(`/insights/${encodeURIComponent(id)}`)
}
