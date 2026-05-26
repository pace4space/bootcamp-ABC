// Data-access seam — the only place the UI touches data.
//
// TODAY (Ex1): imports local JSON.
// EXERCISE 2:  replace each function body with fetch() to the FastAPI backend.
//              Function signatures and return types stay identical; UI never changes.
//
// STUB (commit 2): returns raw data with no filtering or sorting.
// These functions are made correct in commit 3 (GREEN).

import type { Application, Candidate, Position } from './types'
import rawCandidates from '../data/candidates.json'
import rawPositions from '../data/positions.json'
import rawApplications from '../data/applications.json'

const candidates = rawCandidates as unknown as Candidate[]
const positions = rawPositions as unknown as Position[]
const applications = rawApplications as unknown as Application[]

// -- Candidates ---------------------------------------------------------------

export async function getCandidates(): Promise<Candidate[]> {
  // STUB: returns all statuses — commit 3 filters to Active
  return candidates
}

export async function getCandidate(id: string): Promise<Candidate | null> {
  // STUB: lookup is correct but experience is NOT sorted by startYear desc
  return candidates.find(c => c.id === id) ?? null
}

// -- Positions ----------------------------------------------------------------

export async function getPositions(): Promise<Position[]> {
  // STUB: returns all statuses — commit 3 filters to Open
  return positions
}

export async function getPosition(id: string): Promise<Position | null> {
  return positions.find(p => p.id === id) ?? null
}

// -- Applications  ------------------------------------------------------------

export async function getApplicationsByCandidate(
  _candidateId: string,  // _ prefix: intentionally unused in stub; used in commit 3
): Promise<Application[]> {
  // STUB: returns ALL applications regardless of candidateId
  return applications
}

export async function getApplicationsByPosition(
  _positionId: string,
): Promise<Application[]> {
  // STUB: returns ALL applications regardless of positionId
  return applications
}
