import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getPositions } from '../lib/db'
import type { Position } from '../lib/types'

export default function PositionsList() {
  const [positions, setPositions] = useState<Position[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getPositions().then(pos => { setPositions(pos); setLoading(false) })
  }, [])

  const filtered = positions.filter(p =>
    p.title.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  if (loading) return <p className="text-slate-500">Loading...</p>

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Positions</h1>
        <p className="mt-1 text-sm text-slate-500">
          {filtered.length} of {positions.length} open positions
        </p>
      </div>

      <div className="max-w-sm">
        <label htmlFor="search" className="block text-sm font-medium text-slate-700">
          Search by title
        </label>
        <input
          id="search"
          type="text"
          placeholder="e.g. DevOps Engineer"
          value={searchTerm}
          onChange={e => setSearchTerm(e.target.value)}
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {filtered.length === 0 ? (
        <div className="rounded border border-dashed border-slate-300 bg-slate-50 p-8 text-center">
          <p className="text-slate-500">No positions match your search.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {filtered.map(pos => (
            <Link
              key={pos.id}
              to={`/positions/${pos.id}`}
              className="block rounded border border-slate-200 bg-white p-4 transition-colors hover:bg-slate-50"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-1">
                  <h2 className="text-lg font-semibold text-slate-900">{pos.title}</h2>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-sm text-slate-500">
                    {pos.seniority && <span>{pos.seniority}</span>}
                    {pos.location && <span>{pos.location}</span>}
                    {pos.salaryRange && <span>{pos.salaryRange}</span>}
                  </div>
                  <p className="text-xs text-slate-400">{pos.hiringManagerEmail}</p>
                </div>
                <span className="shrink-0 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
                  {pos.status}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}
