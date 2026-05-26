import { createContext, useContext, type ReactNode } from 'react'

// Scaffolded empty in commit 0 so the provider boundary exists from day one.
// Commit 9 fills this with the in-memory working copy of applications plus
// add/remove mutators (changes are NOT persisted until the Ex2 backend).
type ApplicationsContextValue = Record<string, never>

const ApplicationsContext = createContext<ApplicationsContextValue>({})

export function ApplicationsProvider({ children }: { children: ReactNode }) {
  return (
    <ApplicationsContext.Provider value={{}}>
      {children}
    </ApplicationsContext.Provider>
  )
}

export function useApplications() {
  return useContext(ApplicationsContext)
}
