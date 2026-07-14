import { HashRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth/AuthContext'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { GMDashboard } from './pages/GMDashboard'
import { PlayerDashboard } from './pages/PlayerDashboard'

// HashRouter (not BrowserRouter) because this app is ultimately served from
// a static file:// index.html inside Electron (Phase 5) - there is no
// server to fall back arbitrary paths to index.html, so path-based routing
// would 404 on refresh/deep links.

function Dashboard() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/" replace />
  return <Layout>{user.role === 'gm' ? <GMDashboard /> : <PlayerDashboard />}</Layout>
}

function RootRoute() {
  const { user } = useAuth()
  if (user) return <Navigate to="/dashboard" replace />
  return <LoginPage />
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <Routes>
          <Route path="/" element={<RootRoute />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </HashRouter>
    </AuthProvider>
  )
}
