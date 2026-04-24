import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage'
import CandidateListPage from './pages/CandidateListPage'
import CandidateDetailPage from './pages/CandidateDetailPage'
import ProcessingPage from './pages/ProcessingPage'

function Sidebar() {
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
        <NavLink to="/processing" className={({ isActive }) => isActive ? 'active' : ''}>
          <span className="nav-icon">⚙</span> Processing
        </NavLink>
      </nav>

      <a href="#" className="btn-post-job" onClick={e => e.preventDefault()}>
        + Process CVs
      </a>

      <div className="sidebar-bottom">
        <a href="#">⚙ Settings</a>
        <a href="#">? Support</a>
      </div>
    </aside>
  )
}

function Topbar() {
  return (
    <div className="topbar">
      <div className="topbar-search">
        <span className="search-icon">🔍</span>
        <input type="text" placeholder="Search candidates, skills, or folders..." />
      </div>
      <div className="topbar-right">
        <div className="icon-btn">🔔</div>
        <div className="icon-btn">⚙</div>
        <div className="user-chip">
          <div className="avatar">MA</div>
          <div>
            <div className="name">Muhammad Arshyan</div>
            <div className="role">Senior Recruiter</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <div className="main-content">
          <Topbar />
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/candidates" element={<CandidateListPage />} />
            <Route path="/candidates/:candidateId" element={<CandidateDetailPage />} />
            <Route path="/processing" element={<ProcessingPage />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
