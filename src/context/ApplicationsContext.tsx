import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { getAllApplications, createApplication, deleteApplication } from '../lib/db'
import { useAuth } from './AuthContext'
import type { Application } from '../lib/types'

type ApplicationsContextValue = {
  applications: Application[]
  add: (candidateId: string, positionId: string) => Promise<void>
  remove: (appId: string) => Promise<void>
}

const ApplicationsContext = createContext<ApplicationsContextValue>({
  applications: [],
  add: async () => {},
  remove: async () => {},
})

export function ApplicationsProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth()
  const [applications, setApplications] = useState<Application[]>([])

  useEffect(() => {
    if (!token) { setApplications([]); return }
    getAllApplications(token).then(setApplications)
  }, [token])

  async function add(candidateId: string, positionId: string) {
    if (!token) return
    const newApp = await createApplication(candidateId, positionId, token)
    setApplications(prev => [...prev, newApp])
  }

  async function remove(appId: string) {
    if (!token) return
    await deleteApplication(appId, token)
    setApplications(prev => prev.filter(a => a.id !== appId))
  }

  return (
    <ApplicationsContext.Provider value={{ applications, add, remove }}>
      {children}
    </ApplicationsContext.Provider>
  )
}

export function useApplications() {
  return useContext(ApplicationsContext)
}
