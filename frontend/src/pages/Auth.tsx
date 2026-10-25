import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { supabase } from '../lib/supabase'

export function Auth() {
  const { session, loading, authEnabled } = useAuth()
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  if (!loading && session) return <Navigate to="/dashboard" replace />

  if (!authEnabled) {
    return (
      <main className="content-page page-wrap auth-page">
        <div className="auth-card">
          <div className="eyebrow">MUNI ACCOUNT ACCESS</div>
          <h1>Authentication isn’t configured.</h1>
          <p>Configure Auth0 or Supabase Auth to sign in and use your private financial workspace.</p>
          <Link className="button button-primary" to="/dashboard">Continue to Muni <span>↗</span></Link>
        </div>
      </main>
    )
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!supabase) return
    setError('')
    setMessage('')
    setBusy(true)
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
      setError(cause instanceof Error ? cause.message : 'Authentication failed.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="content-page page-wrap auth-page">
      <div className="auth-card">
        <div className="eyebrow">YOUR PRIVATE FINANCIAL WORKSPACE</div>
        <h1>{mode === 'signin' ? 'Welcome back.' : 'Create your account.'}</h1>
        <p>Sign in to manage your financial documents and validation reports.</p>
        <form onSubmit={submit}>
          {mode === 'signup' && <label>Your name<input value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" required /></label>}
          <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
          <label>Password<input type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'signin' ? 'current-password' : 'new-password'} required /></label>
          {error && <p className="form-error" role="alert">{error}</p>}
          {message && <p className="auth-message" role="status">{message}</p>}
          <button className="button button-primary" type="submit" disabled={busy}>{busy ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Create account'} <span>↗</span></button>
        </form>
        <p className="auth-toggle">{mode === 'signin' ? 'New to Muni?' : 'Already have an account?'} <button type="button" onClick={() => { setMode(mode === 'signin' ? 'signup' : 'signin'); setError(''); setMessage('') }}>{mode === 'signin' ? 'Create an account' : 'Sign in'}</button></p>
      </div>
      <Link to="/" className="back-link">← Back home</Link>
    </main>
  )
}
