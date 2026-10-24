import { createContext, useContext, useEffect, useState } from 'react'
import type { PropsWithChildren } from 'react'
import type { Session } from '@supabase/supabase-js'
import { authEnabled, supabase } from '../lib/supabase'

interface AuthValue {
  session: Session | null
  loading: boolean
  authEnabled: boolean
}

const AuthContext = createContext<AuthValue>({ session: null, loading: false, authEnabled: false })

export function AuthProvider({ children }: PropsWithChildren) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(authEnabled)

  useEffect(() => {
    if (!supabase) return
    let active = true
    supabase.auth.getSession()
      .then(({ data, error }) => {
        if (!active) return
        if (error) console.error('Unable to restore the Supabase session', error)
        setSession(data.session)
        setLoading(false)
      })
      .catch((error: unknown) => {
        if (!active) return
        console.error('Unable to restore the Supabase session', error)
        setLoading(false)
      })
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setLoading(false)
    })
    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [])

  return <AuthContext.Provider value={{ session, loading, authEnabled }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
