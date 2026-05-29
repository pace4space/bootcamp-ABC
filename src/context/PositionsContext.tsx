import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getPositions } from '../lib/db'
import { useAuth } from './AuthContext'
import type { Position } from '../lib/types'

type PositionsContextValue = {
  positions: Position[]
  loading: boolean
}

const PositionsContext = createContext<PositionsContextValue>({
  positions: [],
  loading: true,
})

export function PositionsProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [positions, setPositions] = useState<Position[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) { setPositions([]); setLoading(false); return }
    setLoading(true)
    getPositions(token).then(p => { setPositions(p); setLoading(false) })
  }, [token])

  return (
    <PositionsContext.Provider value={{ positions, loading }}>
      {children}
    </PositionsContext.Provider>
  )
}

export function usePositions() {
  return useContext(PositionsContext)
}
