import { describe, expect, it } from 'vitest'
import {
  getApplicationsByCandidate,
  getCandidate,
  getCandidates,
} from './db'

// Real dataset state (see src/data/*.json):
//   cv_004 — Active  | 3 applications (job_001, job_003, job_004) | experience stored oldest-first
//   cv_100 — Archived | 0 applications
//   (11 Active candidates total; cv_100 is the only Archived)

describe('getCandidates', () => {
  it('(a) returns only Active candidates', async () => {
    const result = await getCandidates()
    // Dataset has 11 Active + 1 Archived (cv_100). Archived must be invisible.
    expect(result.length).toBeGreaterThan(0)
    expect(result.every(c => c.status === 'Active')).toBe(true)
    expect(result.find(c => c.id === 'cv_100')).toBeUndefined()
  })
})

describe('getApplicationsByCandidate', () => {
  it('(b) resolves M:N — returns only this candidate\'s applications', async () => {
    const result = await getApplicationsByCandidate('cv_004')
    // cv_004 (Abel McKinney) has exactly 3 apps across job_001, job_003, job_004
    expect(result).toHaveLength(3)
    expect(result.every(a => a.candidateId === 'cv_004')).toBe(true)
    const positionIds = result.map(a => a.positionId).sort()
    expect(positionIds).toEqual(['job_001', 'job_003', 'job_004'])
  })

  it('(d) returns [] gracefully when candidate has no applications', async () => {
    const result = await getApplicationsByCandidate('cv_100')
    // cv_100 is Archived with zero applications; must not crash or return null
    expect(result).toEqual([])
  })
})

describe('getCandidate', () => {
  it('(c) returns experience sorted descending by startYear', async () => {
    const result = await getCandidate('cv_004')
    expect(result).not.toBeNull()
    // cv_004 JSON stores experience oldest-first (2019, 2021) — db layer must sort desc
    const years = result!.experience.map(e => e.startYear)
    expect(years).toEqual([2021, 2019])
  })
})
