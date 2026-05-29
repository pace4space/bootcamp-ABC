import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getCandidate } from '../lib/db'
import { useAuth } from '../context/AuthContext'
import { usePositions } from '../context/PositionsContext'
import { useApplications } from '../context/ApplicationsContext'
import type { Candidate } from '../lib/types'
import AppStatusBadge from '../components/AppStatusBadge'

export default function CandidateProfile() {
  const { id } = useParams<{ id: string }>()
  const { token, user } = useAuth()
  const { positions } = usePositions()
  const { applications, add, remove } = useApplications()

  const [candidate, setCandidate] = useState<Candidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [selectedPositionId, setSelectedPositionId] = useState('')
  const [mutationError, setMutationError] = useState<string | null>(null)

  const canMutate = user?.role === 'admin' || user?.role === 'recruiter'

  useEffect(() => {
    if (!id || !token) return
    setLoading(true)
    getCandidate(id, token).then(c => {
      if (!c) { setNotFound(true); setLoading(false); return }
      setCandidate(c)
      setLoading(false)
    })
  }, [id, token])

  if (loading) return <p className="text-slate-500">Loading...</p>
  if (notFound) return (
    <div className="space-y-2">
      <p className="text-slate-700">Candidate <code>{id}</code> not found.</p>
      <Link to="/candidates" className="text-sm text-blue-600 hover:underline">← Back to list</Link>
    </div>
  )
  if (!candidate) return null

  const candidateApps = applications.filter(a => a.candidateId === candidate.id)
  const posMap = new Map(positions.map(p => [p.id, p.title]))
  const appliedPositionIds = new Set(candidateApps.map(a => a.positionId))
  const availablePositions = positions.filter(p => !appliedPositionIds.has(p.id))

  async function handleAdd() {
    if (!selectedPositionId) return
    setMutationError(null)
    try {
      await add(candidate!.id, selectedPositionId)
      setSelectedPositionId('')
    } catch {
      setMutationError('Failed to add application. Please try again.')
    }
  }

  async function handleRemove(appId: string) {
    setMutationError(null)
    try {
      await remove(appId)
    } catch {
      setMutationError('Failed to remove application. Please try again.')
    }
  }

  return (
    <article className="space-y-8 pb-16">

      <Link to="/candidates" className="text-sm text-blue-600 hover:underline">← All candidates</Link>

      {/* Header */}
      <header className="space-y-1">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900">{candidate.fullName}</h1>
            <p className="mt-1 text-lg text-slate-600">{candidate.headline}</p>
          </div>
          <span className="mt-1 shrink-0 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700">
            {candidate.status}
          </span>
        </div>

        <div className="flex flex-wrap gap-x-4 gap-y-1 pt-2 text-sm text-slate-600">
          <a href={`mailto:${candidate.contact.email}`} className="hover:text-blue-600">
            {candidate.contact.email}
          </a>
          {candidate.contact.phone && <span>{candidate.contact.phone}</span>}
          {candidate.contact.city && <span>{candidate.contact.city}</span>}
          {candidate.contact.linkedinUrl && (
            <a href={candidate.contact.linkedinUrl} target="_blank" rel="noreferrer" className="hover:text-blue-600">
              LinkedIn
            </a>
          )}
          {candidate.contact.githubUrl && (
            <a href={candidate.contact.githubUrl} target="_blank" rel="noreferrer" className="hover:text-blue-600">
              GitHub
            </a>
          )}
        </div>
      </header>

      {/* Original CV link */}
      <div className="flex items-center gap-3 rounded border border-slate-200 bg-slate-50 px-4 py-3 text-sm">
        <span className="text-slate-500">Original CV:</span>
        {candidate.sourceCv.format === 'pdf' ? (
          <a href={candidate.sourceCv.path} target="_blank" rel="noreferrer" className="font-medium text-blue-600 hover:underline">
            {candidate.sourceCv.fileName} (opens in browser)
          </a>
        ) : (
          <a href={candidate.sourceCv.path} download className="font-medium text-blue-600 hover:underline">
            {candidate.sourceCv.fileName} (download)
          </a>
        )}
      </div>

      {/* Summary */}
      {candidate.summary && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Summary</h2>
          <p className="text-slate-700 leading-relaxed">{candidate.summary}</p>
        </section>
      )}

      {/* Skills */}
      {candidate.skills.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Skills</h2>
          <div className="flex flex-wrap gap-2">
            {candidate.skills.map(skill => (
              <span key={skill.id} className="rounded bg-blue-100 px-2 py-1 text-sm text-blue-700">
                {skill.name}
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Experience */}
      {candidate.experience.length > 0 && (
        <section className="space-y-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Experience</h2>
          {candidate.experience.map(exp => (
            <div key={exp.id} className="border-l-2 border-slate-200 pl-4 space-y-1">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold text-slate-900">{exp.role}</span>
                <span className="shrink-0 text-sm text-slate-500">
                  {exp.startYear}–{exp.endYear ?? 'Present'}
                </span>
              </div>
              <p className="text-sm text-slate-600">
                {exp.company}{exp.location ? ` · ${exp.location}` : ''}
              </p>
              {exp.highlights.length > 0 && (
                <ul className="mt-2 space-y-1 list-disc list-inside text-sm text-slate-700">
                  {exp.highlights.map((h, i) => <li key={i}>{h}</li>)}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {/* Education */}
      {candidate.education.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Education</h2>
          {candidate.education.map(edu => (
            <div key={edu.id} className="border-l-2 border-slate-200 pl-4">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold text-slate-900">{edu.degree}</span>
                <span className="shrink-0 text-sm text-slate-500">{edu.startYear}–{edu.endYear}</span>
              </div>
              <p className="text-sm text-slate-600">{edu.institution}</p>
            </div>
          ))}
        </section>
      )}

      {/* Certifications */}
      {candidate.certifications.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Certifications</h2>
          <ul className="space-y-1">
            {candidate.certifications.map(cert => (
              <li key={cert.id} className="flex items-baseline justify-between text-sm">
                <span className="text-slate-800">{cert.name}</span>
                <span className="text-slate-500">{cert.year}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Languages */}
      {candidate.languages.length > 0 && (
        <section className="space-y-2">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Languages</h2>
          <div className="flex flex-wrap gap-3">
            {candidate.languages.map(lang => (
              <span key={lang.id} className="text-sm text-slate-700">
                {lang.name} <span className="text-slate-400">({lang.proficiency})</span>
              </span>
            ))}
          </div>
        </section>
      )}

      {/* Applications */}
      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">
          Applications ({candidateApps.length})
        </h2>

        {mutationError && (
          <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700">{mutationError}</p>
        )}

        {candidateApps.length === 0 ? (
          <p className="text-sm text-slate-500">No applications on file.</p>
        ) : (
          <div className="space-y-2">
            {candidateApps.map(app => (
              <div key={app.id} className="flex items-center justify-between rounded border border-slate-200 bg-white px-4 py-2 text-sm">
                <Link to={`/positions/${app.positionId}`} className="font-medium text-blue-600 hover:underline">
                  {posMap.get(app.positionId) ?? app.positionId}
                </Link>
                <div className="flex items-center gap-2">
                  <AppStatusBadge status={app.status} />
                  {canMutate && (
                    <button
                      onClick={() => handleRemove(app.id)}
                      className="text-xs text-slate-400 hover:text-red-600"
                      aria-label="Remove application"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Add to position — admin/recruiter only */}
        {canMutate && availablePositions.length > 0 && (
          <div className="flex items-center gap-2 pt-1">
            <select
              value={selectedPositionId}
              onChange={e => setSelectedPositionId(e.target.value)}
              className="flex-1 rounded border border-slate-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">Add to a position…</option>
              {availablePositions.map(p => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>
            <button
              onClick={handleAdd}
              disabled={!selectedPositionId}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-40"
            >
              Add
            </button>
          </div>
        )}
      </section>

    </article>
  )
}
