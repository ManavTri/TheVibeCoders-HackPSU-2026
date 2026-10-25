import { useState } from 'react'
import type { ReactNode } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { supabase } from './lib/supabase'
import { Auth } from './pages/Auth'
import { Dashboard } from './pages/Dashboard'
import { Landing } from './pages/Landing'
import { Report } from './pages/Report'
import { Upload } from './pages/Upload'

function Header() {
  const { session, authEnabled } = useAuth()
  const [error, setError] = useState('')

  async function signOut() {
    if (!supabase) {
      setError('Supabase authentication is not configured.')
      return
    }
    try {
      const { error: signOutError } = await supabase.auth.signOut()
      if (signOutError) {
        setError(`Unable to sign out: ${signOutError.message}`)
        return
      }
      setError('')
    } catch (cause) {
      setError(cause instanceof Error ? `Unable to sign out: ${cause.message}` : 'Unable to sign out.')
    }
  }

  return (
    <>
      <header className="site-header page-wrap">
        <Link to="/" className="wordmark"><span className="wordmark-icon">M</span> muni<span className="wordmark-period">.</span></Link>
        <nav>
          <Link to="/dashboard">Overview</Link>
          {authEnabled && session
            ? <button type="button" className="nav-signout" onClick={() => void signOut()}>Sign out</button>
            : authEnabled && <Link to="/auth">Sign in</Link>}
          <Link to="/upload" className="nav-cta">Check documents <span>↗</span></Link>
        </nav>
      </header>
      {error && <p className="nav-error page-wrap" role="alert">{error}</p>}
    </>
  )
}

function Protected({ children }: { children: ReactNode }) {
  const { session, loading, authEnabled } = useAuth()
  if (loading) return <main className="content-page page-wrap loading-state"><div className="loader" /><p>Checking your secure session…</p></main>
  if (authEnabled && !session) return <Navigate to="/auth" replace />
  return children
}

export default function App() {
  return <><Header /><Routes>
    <Route path="/" element={<Landing />} />
    <Route path="/auth" element={<Auth />} />
    <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
    <Route path="/upload" element={<Protected><Upload /></Protected>} />
    <Route path="/report/:id" element={<Protected><Report /></Protected>} />
    <Route path="*" element={<Landing />} />
  </Routes></>
}
