import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getAllApplications } from '../lib/db'
import type { Application } from '../lib/types'

type ApplicationsContextValue = {
  applications: Application[]
  pendingIds: ReadonlySet<string>
  add: (candidateId: string, positionId: string) => void
  remove: (appId: string) => void
}

const ApplicationsContext = createContext<ApplicationsContextValue>({
  applications: [],
  pendingIds: new Set(),
  add: () => {},
  remove: () => {},
})

export function ApplicationsProvider({ children }: { children: ReactNode }) {
  const [applications, setApplications] = useState<Application[]>([])
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    getAllApplications().then(setApplications)
  }, [])

  function add(candidateId: string, positionId: string) {
    if (applications.some(a => a.candidateId === candidateId && a.positionId === positionId)) return
    const id = `app-pending-${Date.now()}`
    const newApp: Application = { id, candidateId, positionId, status: null }
    setApplications(prev => [...prev, newApp])
    setPendingIds(prev => new Set(prev).add(id))
  }

  function remove(appId: string) {
    setApplications(prev => prev.filter(a => a.id !== appId))
    setPendingIds(prev => { const s = new Set(prev); s.delete(appId); return s })
  }

  return (
    <ApplicationsContext.Provider value={{ applications, pendingIds, add, remove }}>
      {children}
    </ApplicationsContext.Provider>
  )
}

export function useApplications() {
  return useContext(ApplicationsContext)
}
