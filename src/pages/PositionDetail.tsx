import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPosition, getCandidate, patchPosition } from '../lib/db'
import { useAuth } from '../context/AuthContext'
import { useApplications } from '../context/ApplicationsContext'
import type { Application, Candidate, Position } from '../lib/types'
import AppStatusBadge from '../components/AppStatusBadge'

type CandidateWithApp = { candidate: Candidate; app: Application }

type EditForm = {
  title: string
  description: string
  status: 'Open' | 'Closed'
  location: string
  seniority: string
  salaryRange: string
  hiringManagerEmail: string
}

export default function PositionDetail() {
  const { id } = useParams<{ id: string }>()
  const { token, user } = useAuth()
  const { applications } = useApplications()

  const [position, setPosition] = useState<Position | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [linked, setLinked] = useState<CandidateWithApp[]>([])

  const [editing, setEditing] = useState(false)
  const [editForm, setEditForm] = useState<EditForm | null>(null)
  const [saving, setSaving] = useState(false)

  const canEdit = user?.role === 'admin' || user?.role === 'recruiter'

  useEffect(() => {
    if (!id || !token) return
    getPosition(id, token).then(pos => {
      if (!pos) { setNotFound(true); setLoading(false); return }
      setPosition(pos)
      setLoading(false)
    })
  }, [id, token])

  // Re-derive linked candidates whenever applications or position changes.
  useEffect(() => {
    if (!id || !position || !token) return
    const posApps = applications.filter(a => a.positionId === id)
    ;(async () => {
      const pairs = await Promise.all(
        posApps.map(async app => {
          const candidate = await getCandidate(app.candidateId, token)
          return candidate ? { candidate, app } : null
        }),
      )
      setLinked(pairs.filter((p): p is CandidateWithApp => p !== null))
    })()
  }, [id, position, applications, token])

  function startEdit() {
    if (!position) return
    setEditForm({
      title: position.title,
      description: position.description,
      status: position.status,
      location: position.location ?? '',
      seniority: position.seniority ?? '',
      salaryRange: position.salaryRange ?? '',
      hiringManagerEmail: position.hiringManagerEmail,
    })
    setEditing(true)
  }

  async function handleSave() {
    if (!editForm || !id || !token) return
    setSaving(true)
    try {
      const updated = await patchPosition(id, {
        title: editForm.title,
        description: editForm.description,
        status: editForm.status,
        location: editForm.location || undefined,
        seniority: editForm.seniority || undefined,
        salaryRange: editForm.salaryRange || undefined,
        hiringManagerEmail: editForm.hiringManagerEmail,
      }, token)
      setPosition(updated)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

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

      <Link to="/positions" className="text-sm text-blue-600 hover:underline">← All positions</Link>

      {/* Header */}
      <header className="space-y-2">
        <div className="flex items-start justify-between gap-4">
          <h1 className="text-3xl font-bold tracking-tight text-slate-900">{position.title}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="shrink-0 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
              {position.status}
            </span>
            {canEdit && !editing && (
              <button
                onClick={startEdit}
                className="shrink-0 rounded border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50"
              >
                Edit
              </button>
            )}
          </div>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
          {position.seniority && <span>{position.seniority}</span>}
          {position.location && <span>{position.location}</span>}
          {position.salaryRange && <span className="font-medium text-slate-700">{position.salaryRange}</span>}
          <span>{position.hiringManagerEmail}</span>
        </div>
      </header>

      {/* Edit form */}
      {editing && editForm && (
        <section className="rounded border border-blue-200 bg-blue-50 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-blue-800">Edit position</h2>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2 space-y-1">
              <label className="block text-xs font-medium text-slate-700">Title</label>
              <input
                value={editForm.title}
                onChange={e => setEditForm({ ...editForm, title: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700">Status</label>
              <select
                value={editForm.status}
                onChange={e => setEditForm({ ...editForm, status: e.target.value as 'Open' | 'Closed' })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              >
                <option value="Open">Open</option>
                <option value="Closed">Closed</option>
              </select>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700">Seniority</label>
              <input
                value={editForm.seniority}
                onChange={e => setEditForm({ ...editForm, seniority: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700">Location</label>
              <input
                value={editForm.location}
                onChange={e => setEditForm({ ...editForm, location: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-medium text-slate-700">Salary range</label>
              <input
                value={editForm.salaryRange}
                onChange={e => setEditForm({ ...editForm, salaryRange: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-xs font-medium text-slate-700">Hiring manager email</label>
              <input
                type="email"
                value={editForm.hiringManagerEmail}
                onChange={e => setEditForm({ ...editForm, hiringManagerEmail: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div className="sm:col-span-2 space-y-1">
              <label className="block text-xs font-medium text-slate-700">Description</label>
              <textarea
                rows={6}
                value={editForm.description}
                onChange={e => setEditForm({ ...editForm, description: e.target.value })}
                className="w-full rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
            <button
              onClick={() => setEditing(false)}
              className="rounded border border-slate-300 px-4 py-1.5 text-sm font-medium text-slate-600 hover:bg-slate-50"
            >
              Cancel
            </button>
          </div>
        </section>
      )}

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
                  <Link
                    to={`/candidates/${candidate.id}`}
                    className="font-medium text-blue-600 hover:underline"
                  >
                    {candidate.fullName}
                  </Link>
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
