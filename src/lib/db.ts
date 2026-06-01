// Data-access seam — the only place the UI touches data.
//
// Ex2: all function bodies replaced with fetch() to the FastAPI backend.
// Function signatures stay identical to Ex1 (+ token param).
// UI components never changed.

import type { Application, Candidate, CandidateMatch, ChatResponse, ChatTurn, Position, PositionMatch } from './types'

async function apiFetch(path: string, token: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...init?.headers,
    },
  })
  if (!res.ok) {
    throw Object.assign(new Error(`API ${res.status}: ${path}`), { status: res.status })
  }
  return res
}

// -- Candidates ---------------------------------------------------------------

export async function getCandidates(token: string): Promise<Candidate[]> {
  return (await apiFetch('/candidates', token)).json()
}

export async function getCandidate(id: string, token: string): Promise<Candidate | null> {
  try {
    return await (await apiFetch(`/candidates/${id}`, token)).json()
  } catch (e: any) {
    if (e.status === 404) return null
    throw e
  }
}

// -- Positions ----------------------------------------------------------------

export async function getPositions(token: string): Promise<Position[]> {
  return (await apiFetch('/positions', token)).json()
}

export async function getPosition(id: string, token: string): Promise<Position | null> {
  try {
    return await (await apiFetch(`/positions/${id}`, token)).json()
  } catch (e: any) {
    if (e.status === 404) return null
    throw e
  }
}

export async function patchPosition(
  id: string,
  patch: Partial<Pick<Position, 'title' | 'description' | 'status' | 'location' | 'seniority' | 'salaryRange' | 'hiringManagerEmail'>>,
  token: string,
): Promise<Position> {
  return (await apiFetch(`/positions/${id}`, token, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  })).json()
}

// -- Applications -------------------------------------------------------------

export async function getAllApplications(token: string): Promise<Application[]> {
  return (await apiFetch('/applications', token)).json()
}

export async function getApplicationsByCandidate(
  candidateId: string,
  token: string,
): Promise<Application[]> {
  return (await apiFetch(`/applications?candidateId=${candidateId}`, token)).json()
}

export async function getApplicationsByPosition(
  positionId: string,
  token: string,
): Promise<Application[]> {
  return (await apiFetch(`/applications?positionId=${positionId}`, token)).json()
}

export async function createApplication(
  candidateId: string,
  positionId: string,
  token: string,
): Promise<Application> {
  return (await apiFetch('/applications', token, {
    method: 'POST',
    body: JSON.stringify({ candidateId, positionId }),
  })).json()
}

export async function deleteApplication(appId: string, token: string): Promise<void> {
  await apiFetch(`/applications/${appId}`, token, { method: 'DELETE' })
}

export async function askChat(
  question: string,
  history: ChatTurn[],
  token: string,
): Promise<ChatResponse> {
  return (await apiFetch('/chat', token, {
    method: 'POST',
    body: JSON.stringify({ question, history }),
  })).json()
}

// -- Ex5 semantic search -------------------------------------------------------

export async function getCandidateMatches(positionId: string, token: string): Promise<CandidateMatch[]> {
  return (await apiFetch(`/positions/${positionId}/candidate-matches`, token)).json()
}

export async function getPositionMatches(candidateId: string, token: string): Promise<PositionMatch[]> {
  return (await apiFetch(`/candidates/${candidateId}/position-matches`, token)).json()
}
