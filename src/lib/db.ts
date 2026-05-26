// Data-access seam — the only place the UI touches data.
//
// TODAY (Ex1): imports local JSON.
// EXERCISE 2:  replace each function body with fetch() to the FastAPI backend.
//              Function signatures and return types stay identical; UI never changes.

import type { Application, Candidate, Position } from './types'
import rawCandidates from '../data/candidates.json'
import rawPositions from '../data/positions.json'
import rawApplications from '../data/applications.json'

const candidates = rawCandidates as unknown as Candidate[]
const positions = rawPositions as unknown as Position[]
const applications = rawApplications as unknown as Application[]

// -- Candidates ---------------------------------------------------------------

export async function getCandidates(): Promise<Candidate[]> {
  return candidates.filter(c => c.status === 'Active')
}

export async function getCandidate(id: string): Promise<Candidate | null> {
  const found = candidates.find(c => c.id === id)
  if (!found) return null
  return {
    ...found,
    experience: [...found.experience].sort((a, b) => b.startYear - a.startYear),
  }
}

// -- Positions ----------------------------------------------------------------

export async function getPositions(): Promise<Position[]> {
  return positions.filter(p => p.status === 'Open')
}

export async function getPosition(id: string): Promise<Position | null> {
  return positions.find(p => p.id === id) ?? null
}

// -- Applications -------------------------------------------------------------

export async function getAllApplications(): Promise<Application[]> {
  return [...applications]
}

export async function getApplicationsByCandidate(
  candidateId: string,
): Promise<Application[]> {
  return applications.filter(a => a.candidateId === candidateId)
}

export async function getApplicationsByPosition(
  positionId: string,
): Promise<Application[]> {
  return applications.filter(a => a.positionId === positionId)
}
