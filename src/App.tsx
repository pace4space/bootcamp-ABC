import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import CandidatesList from './pages/CandidatesList'
import CandidateProfile from './pages/CandidateProfile'
import Compare from './pages/Compare'
import Chat from './pages/Chat'
import Ingest from './pages/Ingest'
import PositionsList from './pages/PositionsList'
import PositionDetail from './pages/PositionDetail'

function ProtectedRoute() {
  const { token } = useAuth()
  const location = useLocation()
  return token ? <Outlet /> : <Navigate to="/login" state={{ from: location.pathname }} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="login" element={<Login />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/candidates" replace />} />
          <Route path="candidates" element={<CandidatesList />} />
          <Route path="candidates/:id" element={<CandidateProfile />} />
          <Route path="chat" element={<Chat />} />
          <Route path="compare" element={<Compare />} />
          <Route path="ingest" element={<Ingest />} />
          <Route path="positions" element={<PositionsList />} />
          <Route path="positions/:id" element={<PositionDetail />} />
          <Route path="*" element={<Navigate to="/candidates" replace />} />
        </Route>
      </Route>
    </Routes>
  )
}
