import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getCandidates, getPositions, getApplicationsByPosition } from '../lib/db'
import type { Candidate, Position } from '../lib/types'

export default function CandidatesList() {
  const [candidates, setCandidates] = useState<Candidate[]>([])
  const [positions, setPositions] = useState<Position[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [loading, setLoading] = useState(true)

  // Load data
  useEffect(() => {
    ;(async () => {
      const [cands, pos] = await Promise.all([getCandidates(), getPositions()])
      setCandidates(cands)
      setPositions(pos)
      setLoading(false)
    })()
  }, [])

  // Filter by search term (name, case-insensitive)
  const bySearch = candidates.filter(c =>
    c.fullName.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  // Position filter: map of position → set of candidate ids with applications
  const [positionAppMap, setPositionAppMap] = useState<Map<string, Set<string>>>(new Map())

  useEffect(() => {
    ;(async () => {
      const appMap = new Map<string, Set<string>>()
      for (const pos of positions) {
        const apps = await getApplicationsByPosition(pos.id)
        appMap.set(pos.id, new Set(apps.map(a => a.candidateId)))
      }
      setPositionAppMap(appMap)
    })()
  }, [positions])

  const finalFiltered = selectedPositionId
    ? bySearch.filter(c => positionAppMap.get(selectedPositionId)?.has(c.id))
    : bySearch

  if (loading) {
    return (
      <section className="space-y-4">
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
        <p className="text-slate-500">Loading...</p>
      </section>
    )
  }

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Candidates</h1>
        <p className="mt-1 text-sm text-slate-500">
          {finalFiltered.length} of {candidates.length} active candidates
        </p>
      </div>

      <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
        <div className="flex-1">
          <label htmlFor="search" className="block text-sm font-medium text-slate-700">
            Search by name
          </label>
          <input
            id="search"
            type="text"
            placeholder="e.g. Aarav Hayes"
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        <div className="flex-1">
          <label htmlFor="position" className="block text-sm font-medium text-slate-700">
            Filter by position (optional)
          </label>
          <select
            id="position"
            value={selectedPositionId}
            onChange={e => setSelectedPositionId(e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All positions</option>
            {positions.map(pos => (
              <option key={pos.id} value={pos.id}>
                {pos.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {finalFiltered.length === 0 ? (
        <div className="rounded border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <p className="text-slate-500">No candidates match your search and filters.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {finalFiltered.map(candidate => (
            <Link
              key={candidate.id}
              to={`/candidates/${candidate.id}`}
              className="block rounded border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-slate-900">{candidate.fullName}</h2>
                  <p className="text-sm text-slate-600">{candidate.headline}</p>
                  {candidate.skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {candidate.skills.slice(0, 5).map(skill => (
                        <span
                          key={skill.id}
                          className="inline-block rounded bg-blue-100 px-2 py-1 text-xs text-blue-700"
                        >
                          {skill.name}
                        </span>
                      ))}
                      {candidate.skills.length > 5 && (
                        <span className="inline-block rounded bg-slate-100 px-2 py-1 text-xs text-slate-600">
                          +{candidate.skills.length - 5}
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="text-right text-sm text-slate-500">
                  {candidate.id}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
