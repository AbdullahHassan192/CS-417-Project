import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import CandidateListPage from './pages/CandidateListPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import ProcessingPage from './pages/ProcessingPage'
import LoginPage from './pages/LoginPage'
import AnalyticsPage from './pages/AnalyticsPage'
import JobsPage from './pages/JobsPage'
import { login as apiLogin, logout as apiLogout } from './services/api'

// ── Auth Context ─────────────────────────────────────────────
const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('talash_user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState(() => localStorage.getItem('talash_token'))

  async function handleLogin(email, password) {
    const data = await apiLogin(email, password)
    setToken(data.access_token)
    setUser(data.user)
    localStorage.setItem('talash_token', data.access_token)
    localStorage.setItem('talash_user', JSON.stringify(data.user))
    return data
  }

  function handleLogout() {
    apiLogout()
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login: handleLogin, logout: handleLogout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

// ── Protected Route ──────────────────────────────────────────
function ProtectedRoute({ children }) {
  const { isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

// ── Sidebar ──────────────────────────────────────────────────
function Sidebar() {
  const { logout } = useAuth()
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="brand">TALASH</div>
        <div className="tagline">Recruitment Portal</div>
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">⊞</span> Dashboard
        </NavLink>
        <NavLink to="/candidates" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">👤</span> Candidates
        </NavLink>
        <NavLink to="/analytics" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">📊</span> Analytics
        </NavLink>
        <NavLink to="/jobs" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">💼</span> Jobs
        </NavLink>
        <NavLink to="/processing" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">⚙</span> Processing
        </NavLink>
      </nav>

      <NavLink to="/jobs" className="btn-post-job">
        + Post New Job
      </NavLink>

      <div className="sidebar-bottom">
        <a href="#" onClick={e => { e.preventDefault(); logout() }}>🚪 Logout</a>
      </div>
    </aside>
  )
}

// ── Topbar ───────────────────────────────────────────────────
function Topbar() {
  const { user } = useAuth()
  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()
    : 'AD'

  return (
    <div className="topbar">
      <div className="topbar-right" style={{ marginLeft: 'auto' }}>
        <div className="user-chip">
          <div className="avatar">{initials}</div>
          <div>
            <div className="name">{user?.full_name || 'Admin'}</div>
            <div className="role">{user?.role || 'Recruiter'}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── App Layout ───────────────────────────────────────────────
function AppLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="main-content">
        <Topbar />
        <Routes>
          <Route path="/" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/candidates" element={<ProtectedRoute><CandidateListPage /></ProtectedRoute>} />
          <Route path="/candidates/:candidateId" element={<ProtectedRoute><CandidateDetailPage /></ProtectedRoute>} />
          <Route path="/analytics" element={<ProtectedRoute><AnalyticsPage /></ProtectedRoute>} />
          <Route path="/jobs" element={<ProtectedRoute><JobsPage /></ProtectedRoute>} />
          <Route path="/processing" element={<ProtectedRoute><ProcessingPage /></ProtectedRoute>} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppLayout />
      </AuthProvider>
    </BrowserRouter>
  )
}
