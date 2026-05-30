import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const linkBase = 'px-3 py-2 rounded-md text-sm font-medium transition-colors'
const linkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? `${linkBase} bg-slate-900 text-white`
    : `${linkBase} text-slate-600 hover:bg-slate-100`

export default function Layout() {
  const { user, logout } = useAuth()
  const canIngest = user?.role === 'admin' || user?.role === 'recruiter'

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
          <span className="text-lg font-semibold tracking-tight">
            Hellio <span className="text-indigo-600">HR</span>
          </span>
          <nav className="flex flex-1 gap-1">
            <NavLink to="/candidates" className={linkClass}>
              Candidates
            </NavLink>
            <NavLink to="/positions" className={linkClass}>
              Positions
            </NavLink>
            <NavLink to="/compare" className={linkClass}>
              Compare
            </NavLink>
            {canIngest && (
              <NavLink to="/ingest" className={linkClass}>
                Upload CV
              </NavLink>
            )}
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">{user?.email}</span>
            <button
              onClick={logout}
              className="rounded border border-slate-200 px-3 py-1.5 text-slate-600 hover:bg-slate-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
