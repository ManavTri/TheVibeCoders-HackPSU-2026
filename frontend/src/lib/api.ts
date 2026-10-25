import { supabase } from './supabase'
import type { DocumentCorrection, DocumentRecord, DocumentType, Insights, ValidationReport } from '../types/api'

const configuredUrl = import.meta.env.VITE_API_URL as string | undefined
if (!configuredUrl && import.meta.env.PROD) {
  throw new Error('VITE_API_URL is not set. Set it in the Vercel project settings and redeploy.')
}
const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const { data, error } = supabase ? await supabase.auth.getSession() : { data: { session: null }, error: null }
  if (error) throw new Error(`Unable to read the Supabase session: ${error.message}`)
  const headers = new Headers(init?.headers)
  if (data.session?.access_token) headers.set('Authorization', `Bearer ${data.session.access_token}`)
  const response = await fetch(`${apiUrl}/api${path}`, { ...init, headers })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      detail?: string | { message?: string }
    } | null
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : detail?.message
    throw new Error(message || `Request failed (${response.status})`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function uploadDocument(file: File, documentType: DocumentType): Promise<DocumentRecord> {
  const body = new FormData()
  body.append('file', file)
  body.append('document_type', documentType)
  return request<DocumentRecord>('/documents', { method: 'POST', body })
}

export function getDocuments(): Promise<DocumentRecord[]> {
  return request<DocumentRecord[]>('/documents')
}

export function getDocument(id: string): Promise<DocumentRecord> {
  return request<DocumentRecord>(`/documents/${encodeURIComponent(id)}`)
}

export function correctDocument(id: string, correction: DocumentCorrection): Promise<DocumentRecord> {
  return request<DocumentRecord>(`/documents/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(correction),
  })
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function createValidation(documentIds: string[]): Promise<ValidationReport> {
  return request<ValidationReport>('/validations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds }),
  })
}

export function getReport(id: string): Promise<ValidationReport> {
  return request<ValidationReport>(`/validations/${encodeURIComponent(id)}`)
}

export function getInsights(runId: string): Promise<Insights> {
  return request<Insights>('/insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
  })
}
