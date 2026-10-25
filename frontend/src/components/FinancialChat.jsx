import { useEffect, useRef, useState } from 'react'
import {
  cancelChatAction,
  confirmChatAction,
  sendChatMessage,
} from '../lib/backend'

const CHAT_LIMIT = 20
const CHAT_WINDOW_MS = 10 * 60 * 1000
const HELLO = 'Hi! I can help compare your uploaded financial documents, explain findings, and prepare edits or a fresh check. Any change or recheck requires your confirmation.'

function currentTimeMs() {
  return Date.now()
}

function actionDetails(action) {
  if (action.preview) {
    const { field, current, proposed } = action.preview
    return `${field.replaceAll('_', ' ')}: ${current ?? 'not set'} → ${proposed ?? 'not set'}`
  }
  const { field, value } = action.args || {}
  if (!field) return null
  return `${field.replaceAll('_', ' ')} → ${value ?? 'blank'}`
}

export function FinancialChat({ onDocumentsChanged, onRecheck }) {
  const [messages, setMessages] = useState([{ role: 'assistant', content: HELLO }])
  const [pendingActions, setPendingActions] = useState([])
  const [suggestions, setSuggestions] = useState([
    'Check my current findings',
    'Show upcoming deadlines',
  ])
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [busyActionId, setBusyActionId] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const requestTimes = useRef([])
  const messageList = useRef(null)
  const requestInFlight = useRef(false)
  const actionInFlight = useRef(false)
  const pendingActionRef = useRef([])

  useEffect(() => {
    messageList.current?.scrollTo({ top: messageList.current.scrollHeight, behavior: 'smooth' })
  }, [messages, pendingActions])

  async function send(text) {
    const nextMessage = text.trim()
    if (!nextMessage || requestInFlight.current || pendingActionRef.current.length > 0) return
    const now = currentTimeMs()
    requestTimes.current = requestTimes.current.filter((time) => now - time < CHAT_WINDOW_MS)
    if (requestTimes.current.length >= CHAT_LIMIT) {
      setError('This device has reached its limit of 20 chat requests per 10 minutes. Please wait before trying again.')
      return
    }
    requestTimes.current.push(now)
    requestInFlight.current = true

    const history = messages.slice(-12).map((turn) => ({
      role: turn.role,
      content: turn.content.slice(0, 2000),
    }))
    setMessages((current) => [...current, { role: 'user', content: nextMessage }])
    setMessage('')
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const response = await sendChatMessage(nextMessage, history)
      const nextActions = response.pendingActions || []
      if (nextActions.length > 0) {
        const knownIds = new Set(pendingActionRef.current.map((action) => action.id))
        const uniqueActions = nextActions.filter((action) => !knownIds.has(action.id))
        pendingActionRef.current = [...pendingActionRef.current, ...uniqueActions]
        setPendingActions(pendingActionRef.current)
      } else {
        setMessages((current) => [
          ...current,
          { role: 'assistant', content: response.reply, sources: response.sources || [] },
        ])
        setSuggestions(response.suggestions || [])
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The chat request failed.')
      setMessages((current) => current.slice(0, -1))
    } finally {
      requestInFlight.current = false
      setBusy(false)
    }
  }

  async function confirmAction(action) {
    if (actionInFlight.current) return
    actionInFlight.current = true
    setBusyActionId(action.id)
    setError('')
    setNotice('')
    try {
      const result = await confirmChatAction(action.id)
      pendingActionRef.current = pendingActionRef.current.filter((item) => item.id !== action.id)
      setPendingActions(pendingActionRef.current)
      if (result.reportId) {
        await onRecheck(result.reportId)
      } else {
        await onDocumentsChanged()
      }
      setNotice(result.message)
      setMessages((current) => [...current, { role: 'assistant', content: result.message }])
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The action could not be completed.')
    } finally {
      actionInFlight.current = false
      setBusyActionId('')
    }
  }

  async function cancelAction(action) {
    if (actionInFlight.current) return
    actionInFlight.current = true
    setBusyActionId(action.id)
    setError('')
    try {
      await cancelChatAction(action.id)
      pendingActionRef.current = pendingActionRef.current.filter((item) => item.id !== action.id)
      setPendingActions(pendingActionRef.current)
      setNotice('Pending action cancelled; no document changes were made.')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'The action could not be cancelled.')
    } finally {
      actionInFlight.current = false
      setBusyActionId('')
    }
  }

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <h2 className="font-semibold text-slate-900">EduCash assistant</h2>
          <p className="mt-1 text-xs text-slate-500">Document-grounded help · no saved chat history</p>
        </div>
        <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-900">
          20 requests / 10 minutes
        </span>
      </header>

      <div
        ref={messageList}
        className="max-h-[52vh] min-h-72 space-y-4 overflow-y-auto bg-slate-50 p-4 sm:p-6"
        aria-live="polite"
        aria-label="Chat conversation"
      >
        {messages.map((turn, index) => (
          <article
            key={`${index}-${turn.role}`}
            className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-6 ${
              turn.role === 'user'
                ? 'ml-auto bg-emerald-800 text-white'
                : 'border border-slate-200 bg-white text-slate-800'
            }`}
          >
            <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-70">
              {turn.role === 'user' ? 'You' : 'EduCash'}
            </p>
            {turn.content}
            {turn.sources?.length > 0 && (
              <p className="mt-2 border-t border-slate-200 pt-2 text-xs text-slate-500">
                Sources: {turn.sources.map((source) => source.filename).join(', ')}
              </p>
            )}
          </article>
        ))}
        {busy && <p className="text-sm text-slate-500" role="status">Checking your documents…</p>}

        {pendingActions.map((action) => (
          <article key={action.id} className="rounded-xl border border-amber-300 bg-amber-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wider text-amber-900">Confirmation required</p>
            <h3 className="mt-1 font-semibold text-slate-900">{action.summary}</h3>
            {actionDetails(action) && (
              <p className="mt-2 break-words text-sm text-slate-700">{actionDetails(action)}</p>
            )}
            <p className="mt-2 text-xs leading-5 text-slate-600">
              Nothing has changed yet. Confirm only if the proposed change is correct.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busyActionId === action.id}
                onClick={() => void confirmAction(action)}
                className="rounded-lg bg-emerald-800 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
              >
                {busyActionId === action.id ? 'Working…' : 'Confirm this action'}
              </button>
              <button
                type="button"
                disabled={busyActionId === action.id}
                onClick={() => void cancelAction(action)}
                className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-semibold text-slate-700 disabled:opacity-50"
              >
                Cancel action
              </button>
            </div>
          </article>
        ))}
      </div>

      <div className="space-y-3 border-t border-slate-200 p-4 sm:p-5">
        {error && <p className="rounded-lg bg-rose-50 p-3 text-sm text-rose-800" role="alert">{error}</p>}
        {notice && <p className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800" role="status">{notice}</p>}
        {pendingActions.length === 0 && suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={busy || pendingActions.length > 0}
                onClick={() => void send(suggestion)}
                className="rounded-full border border-slate-300 bg-white px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        <form
          className="flex flex-col gap-2 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault()
            void send(message)
          }}
        >
          <label className="sr-only" htmlFor="financial-chat-message">Message the EduCash assistant</label>
          <textarea
            id="financial-chat-message"
            rows={2}
            maxLength={2000}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            disabled={busy || pendingActions.length > 0}
            placeholder="Ask about your documents, findings, or deadlines…"
            className="min-h-12 flex-1 resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm text-slate-900 outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
          />
          <button
            type="submit"
            disabled={busy || pendingActions.length > 0 || !message.trim()}
            className="min-h-12 rounded-xl bg-emerald-800 px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? 'Sending…' : 'Send'}
          </button>
        </form>
        <p className="text-[11px] leading-5 text-slate-500">
          Changes, re-extraction, and rechecks are never automatic. Each proposed action requires your explicit confirmation.
        </p>
      </div>
    </section>
  )
}
