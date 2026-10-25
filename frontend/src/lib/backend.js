import { createClient } from '@supabase/supabase-js'
import { auth0Configured, getAuth0AccessToken } from './auth0'

const apiUrl = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '')
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY
const supabaseConfigured = Boolean(supabaseUrl && supabaseAnonKey)
const auth0VariablesPresent = Boolean(import.meta.env.VITE_AUTH0_DOMAIN || import.meta.env.VITE_AUTH0_CLIENT_ID || import.meta.env.VITE_AUTH0_AUDIENCE)
const supabaseVariablesPresent = Boolean(supabaseUrl || supabaseAnonKey)

export const preferredAuth = auth0Configured ? 'auth0' : supabaseConfigured ? 'supabase' : null
export const authConfigurationIncomplete = (!auth0Configured && auth0VariablesPresent && !supabaseConfigured)
  || (!supabaseConfigured && supabaseVariablesPresent && !auth0Configured)
export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null
export const remoteApiWithoutAuth = Boolean(import.meta.env.VITE_API_URL)
  && !/localhost|127\.0\.0\.1/i.test(import.meta.env.VITE_API_URL)
  && !preferredAuth

async function fetchApi(path, init) {
  let accessToken = null
  if (auth0Configured) {
    try {
      accessToken = await getAuth0AccessToken()
    } catch (error) {
      throw new Error(`Unable to read the Auth0 session: ${error.message}`)
    }
  } else if (supabase) {
    const { data, error } = await supabase.auth.getSession()
    if (error) throw new Error(`Unable to read the Supabase session: ${error.message}`)
    accessToken = data.session?.access_token
  }

  const headers = new Headers(init?.headers)
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  const response = await fetch(`${apiUrl}/api${path}`, { ...init, headers })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = body?.detail
    const message = typeof detail === 'string'
      ? detail
      : typeof detail?.message === 'string'
        ? detail.message
        : Array.isArray(detail)
          ? detail.map((item) => item.msg).filter(Boolean).join('; ')
          : null
    throw new Error(message || `Request failed (${response.status})`)
  }
  return response
}

async function requestJson(path, init) {
  const response = await fetchApi(path, init)
  if (response.status === 204) return undefined
  return response.json()
}

export function getDocuments(state = 'active') {
  return requestJson(`/documents?state=${encodeURIComponent(state)}`)
}

export function getCurrentFindingsReport() {
  return requestJson('/findings/report')
}

export function sendChatMessage(message, history = []) {
  return requestJson('/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
}

export function confirmChatAction(id) {
  return requestJson(`/ai/actions/${encodeURIComponent(id)}/confirm`, { method: 'POST' })
}

export function cancelChatAction(id) {
  return requestJson(`/ai/actions/${encodeURIComponent(id)}/cancel`, { method: 'POST' })
}

export function getValidation(id) {
  return requestJson(`/validations/${encodeURIComponent(id)}`)
}

export function uploadDocument(file, documentType) {
  const body = new FormData()
  body.append('file', file)
  body.append('document_type', documentType)
  return requestJson('/documents', { method: 'POST', body })
}

export function correctDocument(id, correction) {
  return requestJson(`/documents/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(correction),
  })
}

export function archiveDocument(id) {
  return requestJson(`/documents/${encodeURIComponent(id)}/archive`, { method: 'POST' })
}

export function restoreDocument(id) {
  return requestJson(`/documents/${encodeURIComponent(id)}/restore`, { method: 'POST' })
}

export function softDeleteDocument(id) {
  return requestJson(`/documents/${encodeURIComponent(id)}/delete`, { method: 'POST' })
}

export function permanentlyDeleteDocument(id) {
  return requestJson(`/documents/${encodeURIComponent(id)}`, { method: 'DELETE' })
}

export function createValidation(documentIds) {
  return requestJson('/validations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds }),
  })
}

export function createInsights(runId) {
  return requestJson('/insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId }),
  })
}

export async function getDocumentPdf(id) {
  const response = await fetchApi(`/documents/${encodeURIComponent(id)}/file`)
  return response.blob()
}
