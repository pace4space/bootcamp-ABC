import { describe, expect, it } from 'vitest'
import {
  getApplicationsByCandidate,
  getCandidate,
  getCandidates,
} from './db'

// Ex1 tests verified the JSON-backed db.ts implementation.
// Ex2 replaced those bodies with fetch() — these tests require a live API server.
// The same contracts are verified by api/tests/ (36 pytest cases).
// These are skipped until Ex3 introduces a fetch-mock or test server fixture.

const TOKEN = 'test-token'

describe.skip('getCandidates', () => {
  it('(a) returns only Active candidates', async () => {
    const result = await getCandidates(TOKEN)
    expect(result.length).toBeGreaterThan(0)
    expect(result.every(c => c.status === 'Active')).toBe(true)
    expect(result.find(c => c.id === 'cv_100')).toBeUndefined()
  })
})

describe.skip('getApplicationsByCandidate', () => {
  it('(b) resolves M:N — returns only this candidate\'s applications', async () => {
    const result = await getApplicationsByCandidate('cv_004', TOKEN)
    expect(result).toHaveLength(3)
    expect(result.every(a => a.candidateId === 'cv_004')).toBe(true)
    const positionIds = result.map(a => a.positionId).sort()
    expect(positionIds).toEqual(['job_001', 'job_003', 'job_004'])
  })

  it('(d) returns [] gracefully when candidate has no applications', async () => {
    const result = await getApplicationsByCandidate('cv_100', TOKEN)
    expect(result).toEqual([])
  })
})

describe.skip('getCandidate', () => {
  it('(c) returns experience sorted descending by startYear', async () => {
    const result = await getCandidate('cv_004', TOKEN)
    expect(result).not.toBeNull()
    const years = result!.experience.map(e => e.startYear)
    expect(years).toEqual([2021, 2019])
  })
})
