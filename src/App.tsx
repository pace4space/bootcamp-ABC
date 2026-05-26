import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import CandidatesList from './pages/CandidatesList'
import CandidateProfile from './pages/CandidateProfile'
import Compare from './pages/Compare'
import PositionsList from './pages/PositionsList'
import PositionDetail from './pages/PositionDetail'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/candidates" replace />} />
        <Route path="candidates" element={<CandidatesList />} />
        <Route path="candidates/:id" element={<CandidateProfile />} />
        <Route path="compare" element={<Compare />} />
        <Route path="positions" element={<PositionsList />} />
        <Route path="positions/:id" element={<PositionDetail />} />
        <Route path="*" element={<Navigate to="/candidates" replace />} />
      </Route>
    </Routes>
  )
}
