import { describe, expect, it } from 'vitest'
import {
  getApplicationsByCandidate,
  getCandidate,
  getCandidates,
} from './db'

// Fixture state (see src/data/*.json):
//   cv_001 — Active  | 2 applications (job_001, job_002) | experience stored out-of-order
//   cv_002 — Archived | 0 applications
//   cv_003 — not in candidates.json | 1 application (exists to pollute unfiltered queries)

describe('getCandidates', () => {
  it('(a) returns only Active candidates', async () => {
    const result = await getCandidates()
    // Fixture has 1 Active + 1 Archived. Archived must be invisible.
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('cv_001')
    expect(result.every(c => c.status === 'Active')).toBe(true)
  })
})

describe('getApplicationsByCandidate', () => {
  it('(b) resolves M:N — returns only this candidate\'s applications', async () => {
    const result = await getApplicationsByCandidate('cv_001')
    // cv_001 has exactly 2 apps; cv_003 app must not appear
    expect(result).toHaveLength(2)
    expect(result.every(a => a.candidateId === 'cv_001')).toBe(true)
    const positionIds = result.map(a => a.positionId).sort()
    expect(positionIds).toEqual(['job_001', 'job_002'])
  })

  it('(d) returns [] gracefully when candidate has no applications', async () => {
    const result = await getApplicationsByCandidate('cv_002')
    // cv_002 is Archived with zero applications; must not crash or return null
    expect(result).toEqual([])
  })
})

describe('getCandidate', () => {
  it('(c) returns experience sorted descending by startYear', async () => {
    const result = await getCandidate('cv_001')
    expect(result).not.toBeNull()
    // Fixture stores experience oldest-first (2021, 2023) — db layer must sort desc
    const years = result!.experience.map(e => e.startYear)
    expect(years).toEqual([2023, 2021])
  })
})
