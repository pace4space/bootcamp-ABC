import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext.tsx'
import { CandidatesProvider } from './context/CandidatesContext.tsx'
import { PositionsProvider } from './context/PositionsContext.tsx'
import { ApplicationsProvider } from './context/ApplicationsContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <CandidatesProvider>
          <PositionsProvider>
            <ApplicationsProvider>
              <App />
            </ApplicationsProvider>
          </PositionsProvider>
        </CandidatesProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
