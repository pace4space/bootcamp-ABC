import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPosition, getCandidate } from '../lib/db'
import { useApplications } from '../context/ApplicationsContext'
import type { Application, Candidate, Position } from '../lib/types'
import AppStatusBadge from '../components/AppStatusBadge'

type CandidateWithApp = { candidate: Candidate; app: Application }

export default function PositionDetail() {
  const { id } = useParams<{ id: string }>()
  const [position, setPosition] = useState<Position | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [linked, setLinked] = useState<CandidateWithApp[]>([])

  const { applications, pendingIds } = useApplications()

  useEffect(() => {
    if (!id) return
    getPosition(id).then(pos => {
      if (!pos) { setNotFound(true); setLoading(false); return }
      setPosition(pos)
      setLoading(false)
    })
  }, [id])

  // Re-derive linked candidates whenever applications or position changes.
  // This keeps PositionDetail live when the user adds a candidate from CandidateProfile.
  useEffect(() => {
    if (!id || !position) return
    const posApps = applications.filter(a => a.positionId === id)
    ;(async () => {
      const pairs = await Promise.all(
        posApps.map(async app => {
          const candidate = await getCandidate(app.candidateId)
          return candidate ? { candidate, app } : null
        }),
      )
      setLinked(pairs.filter((p): p is CandidateWithApp => p !== null))
    })()
  }, [id, position, applications])

  if (loading) return <p className="text-slate-500">Loading...</p>
  if (notFound) return (
    <div className="space-y-2">
      <p className="text-slate-700">Position <code>{id}</code> not found.</p>
      <Link to="/positions" className="text-sm text-blue-600 hover:underline">← Back to list</Link>
    </div>
  )
  if (!position) return null

  return (
    <article className="space-y-8 pb-16">

      {/* Back link */}
      <Link to="/positions" className="text-sm text-blue-600 hover:underline">← All positions</Link>

      {/* Header */}
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{position.title}</h1>
          <span className="mt-1 shrink-0 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            {position.status}
          </span>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
          {position.seniority && <span>{position.seniority}</span>}
          {position.location && <span>{position.location}</span>}
          {position.salaryRange && <span className="font-medium text-slate-700">{position.salaryRange}</span>}
          <span>{position.hiringManagerEmail}</span>
        </div>
      </header>

      {/* Source email link */}
      <div className="flex items-center gap-3 rounded border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-500">Source email:</span>
        <a
          href={position.sourceDocument.path}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-blue-600 hover:underline"
        >
          {position.sourceDocument.fileName}
        </a>
      </div>

      {/* Requirements */}
      {position.requirements && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Requirements</h2>
          {position.requirements.mustHave.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500 uppercase tracking-wide">Must-have</p>
              <ul className="space-y-1 list-disc list-inside text-sm text-slate-700">
                {position.requirements.mustHave.map((req, i) => <li key={i}>{req}</li>)}
              </ul>
            </div>
          )}
          {position.requirements.niceToHave.length > 0 && (
            <div>
              <p className="mb-1 text-xs font-medium text-slate-500 uppercase tracking-wide">Nice-to-have</p>
              <ul className="space-y-1 list-disc list-inside text-sm text-slate-700">
                {position.requirements.niceToHave.map((req, i) => <li key={i}>{req}</li>)}
              </ul>
            </div>
          )}
        </section>
      )}

      {/* Description */}
      {position.description && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Description</h2>
          <p className="whitespace-pre-line text-sm text-slate-700 leading-relaxed">{position.description}</p>
        </section>
      )}

      {/* Linked candidates */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Candidates ({linked.length})
        </h2>
        {linked.length === 0 ? (
          <p className="text-sm text-slate-500">No candidates linked to this position.</p>
        ) : (
          <div className="space-y-2">
            {linked.map(({ candidate, app }) => (
              <div key={app.id} className="flex items-center justify-between rounded border border-slate-200 bg-white px-4 py-3">
                <div>
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/candidates/${candidate.id}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {candidate.fullName}
                    </Link>
                    {pendingIds.has(app.id) && (
                      <span className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                        Pending · not saved until Ex2
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500">{candidate.headline}</p>
                </div>
                <AppStatusBadge status={app.status} />
              </div>
            ))}
          </div>
        )}
      </section>

    </article>
  )
}
