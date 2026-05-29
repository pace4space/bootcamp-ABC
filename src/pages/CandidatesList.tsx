import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useCandidates } from '../context/CandidatesContext'
import { usePositions } from '../context/PositionsContext'
import { useApplications } from '../context/ApplicationsContext'

export default function CandidatesList() {
  const { candidates, loading: candidatesLoading } = useCandidates()
  const { positions, loading: positionsLoading } = usePositions()
  const { applications } = useApplications()

  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPositionId, setSelectedPositionId] = useState('')

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
