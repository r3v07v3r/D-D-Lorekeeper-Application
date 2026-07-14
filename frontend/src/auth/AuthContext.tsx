import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, ApiError } from '../api/client'
import type { UserPublic } from '../types/api'

const STORAGE_KEY = 'lorekeeper_session'

interface StoredSession {
  token: string
  user: UserPublic
}

interface AuthContextValue {
  token: string | null
  user: UserPublic | null
  loginAs: (userId: number) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<StoredSession | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as StoredSession) : null
  })

  useEffect(() => {
    if (session) localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    else localStorage.removeItem(STORAGE_KEY)
  }, [session])

  // If a stored token has gone stale (backend restarted since login - the
  // session store is in-memory, see backend/app/auth.py), drop it so the
  // user falls back to the login screen instead of hitting 401s everywhere.
  useEffect(() => {
    if (!session) return
    api.get('/auth/me', session.token).catch((err) => {
      if (err instanceof ApiError && err.status === 401) setSession(null)
    })
  }, [])

  async function loginAs(userId: number) {
    const response = await api.post<{ token: string; user: UserPublic }>('/auth/login', { user_id: userId })
    setSession({ token: response.token, user: response.user })
  }

  function logout() {
    if (session) api.post('/auth/logout', undefined, session.token).catch(() => {})
    setSession(null)
  }

  return (
    <AuthContext.Provider
      value={{ token: session?.token ?? null, user: session?.user ?? null, loginAs, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
