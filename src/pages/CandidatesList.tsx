import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useCandidates } from '../context/CandidatesContext'
import { usePositions } from '../context/PositionsContext'
import { useApplications } from '../context/ApplicationsContext'

export default function CandidatesList() {
  const { candidates, loading: candidatesLoading } = useCandidates()
  const { positions, loading: positionsLoading } = usePositions()
  const { applications } = useApplications()
  const navigate = useNavigate()

  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [compareSet, setCompareSet] = useState<Set<string>>(new Set())

  function toggleCompare(id: string) {
    setCompareSet(prev => {
      const next = new Set(prev)
      if (next.has(id)) { next.delete(id); return next }
      if (next.size >= 2) return prev
      next.add(id)
      return next
    })
  }

  function handleCompare() {
    const [a, b] = [...compareSet]
    navigate(`/compare?a=${a}&b=${b}`)
  }

  // Build position → candidate set from context applications (no extra HTTP requests)
  const positionAppMap = useMemo(() => {
    const map = new Map<string, Set<string>>()
    for (const app of applications) {
      if (!map.has(app.positionId)) map.set(app.positionId, new Set())
      map.get(app.positionId)!.add(app.candidateId)
    }
    return map
  }, [applications])

  const bySearch = candidates.filter(c =>
    c.fullName.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const finalFiltered = selectedPositionId
    ? bySearch.filter(c => positionAppMap.get(selectedPositionId)?.has(c.id))
    : bySearch

  if (candidatesLoading || positionsLoading) {
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
        <div className="grid gap-3">
          {finalFiltered.map(candidate => (
            <div key={candidate.id} className="flex items-start gap-3 rounded border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50">
              <input
                type="checkbox"
                checked={compareSet.has(candidate.id)}
                onChange={() => toggleCompare(candidate.id)}
                disabled={!compareSet.has(candidate.id) && compareSet.size >= 2}
                className="mt-1 h-4 w-4 cursor-pointer accent-indigo-600 disabled:cursor-not-allowed disabled:opacity-40"
              />
              <Link to={`/candidates/${candidate.id}`} className="flex min-w-0 flex-1 items-start justify-between">
                <div className="flex-1">
                  <h2 className="text-lg font-semibold text-slate-900">{candidate.fullName}</h2>
                  <p className="text-sm text-slate-600">{candidate.headline}</p>
                  {candidate.skills.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {candidate.skills.slice(0, 5).map(skill => (
                        <span key={skill.id} className="inline-block rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">
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
                <div className="shrink-0 text-right text-sm text-slate-400">{candidate.id}</div>
              </Link>
            </div>
          ))}
        </div>
      )}

      {compareSet.size > 0 && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-slate-200 bg-white px-6 py-3 shadow-lg">
          <div className="mx-auto flex max-w-6xl items-center justify-between">
            <p className="text-sm text-slate-600">
              {compareSet.size === 1 ? 'Select one more to compare' : '2 candidates selected'}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setCompareSet(new Set())}
                className="rounded border border-slate-300 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                Clear
              </button>
              <button
                onClick={handleCompare}
                disabled={compareSet.size < 2}
                className="rounded bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
              >
                Compare →
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
