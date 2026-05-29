import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getCandidates } from '../lib/db'
import { useAuth } from './AuthContext'
import type { Candidate } from '../lib/types'

type CandidatesContextValue = {
  candidates: Candidate[]
  loading: boolean
}

const CandidatesContext = createContext<CandidatesContextValue>({
  candidates: [],
  loading: true,
})

export function CandidatesProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) { setCandidates([]); setLoading(false); return }
    setLoading(true)
    getCandidates(token).then(c => { setCandidates(c); setLoading(false) })
  }, [token])

  return (
    <CandidatesContext.Provider value={{ candidates, loading }}>
      {children}
    </CandidatesContext.Provider>
  )
}

export function useCandidates() {
  return useContext(CandidatesContext)
}
