import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getCandidate } from '../lib/db'
import { useAuth } from '../context/AuthContext'
import type { Candidate, CandidateDiff, ExperienceItem, EducationItem, Certification } from '../lib/types'

function computeDiff(a: Candidate, b: Candidate): CandidateDiff {
  const namesB = new Set(b.skills.map(s => s.name))
  const namesA = new Set(a.skills.map(s => s.name))
  return {
    sharedSkills: a.skills.filter(s => namesB.has(s.name)),
    onlyInA:      a.skills.filter(s => !namesB.has(s.name)),
    onlyInB:      b.skills.filter(s => !namesA.has(s.name)),
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CandidateHeader({ candidate, accent }: { candidate: Candidate; accent: 'blue' | 'purple' }) {
  const border = accent === 'blue' ? 'border-l-blue-400' : 'border-l-purple-400'
  return (
    <div className={`rounded border border-slate-200 border-l-4 bg-white p-4 ${border}`}>
      <Link to={`/candidates/${candidate.id}`} className="text-lg font-bold text-slate-900 hover:underline">
        {candidate.fullName}
      </Link>
      <p className="mt-0.5 text-sm text-slate-600">{candidate.headline}</p>
      {candidate.contact.city && (
        <p className="mt-1 text-xs text-slate-400">{candidate.contact.city}</p>
      )}
    </div>
  )
}

function ExperienceColumn({ items }: { items: ExperienceItem[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">No experience on file.</p>
  return (
    <div className="space-y-3">
      {items.map(exp => (
        <div key={exp.id} className="border-l-2 border-slate-200 pl-3 space-y-0.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-semibold text-slate-900">{exp.role}</span>
            <span className="shrink-0 text-xs text-slate-500">
              {exp.startYear}–{exp.endYear ?? 'Present'}
            </span>
          </div>
          <p className="text-xs text-slate-600">
            {exp.company}{exp.location ? ` · ${exp.location}` : ''}
          </p>
        </div>
      ))}
    </div>
  )
}

function EducationColumn({ items }: { items: EducationItem[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">—</p>
  return (
    <div className="space-y-2">
      {items.map(edu => (
        <div key={edu.id} className="border-l-2 border-slate-200 pl-3">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-semibold text-slate-900">{edu.degree}</span>
            <span className="shrink-0 text-xs text-slate-500">{edu.startYear}–{edu.endYear}</span>
          </div>
          <p className="text-xs text-slate-600">{edu.institution}</p>
        </div>
      ))}
    </div>
  )
}

function CertColumn({ items }: { items: Certification[] }) {
  if (items.length === 0) return <p className="text-sm text-slate-400">—</p>
  return (
    <ul className="space-y-1">
      {items.map(cert => (
        <li key={cert.id} className="flex items-baseline justify-between text-sm">
          <span className="text-slate-800">{cert.name}</span>
          <span className="shrink-0 text-xs text-slate-500">{cert.year}</span>
        </li>
      ))}
    </ul>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Compare() {
  const { token } = useAuth()
  const [searchParams] = useSearchParams()
  const aId = searchParams.get('a')
  const bId = searchParams.get('b')

  const [a, setA] = useState<Candidate | null>(null)
  const [b, setB] = useState<Candidate | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState<string | null>(null)

  useEffect(() => {
    if (!token || !aId || !bId) { setLoading(false); return }
    ;(async () => {
      const [ca, cb] = await Promise.all([getCandidate(aId, token), getCandidate(bId, token)])
      if (!ca) { setNotFound(aId); setLoading(false); return }
      if (!cb) { setNotFound(bId); setLoading(false); return }
      setA(ca)
      setB(cb)
      setLoading(false)
    })()
  }, [aId, bId, token])

  if (loading) return <p className="text-slate-500">Loading...</p>

  if (!aId || !bId) return (
    <div className="space-y-3">
      <h1 className="text-2xl font-semibold tracking-tight">Compare Candidates</h1>
      <p className="text-slate-500">
        Add <code className="rounded bg-slate-100 px-1 py-0.5 text-sm">?a=cv_150&amp;b=cv_202</code> to the
        URL to compare two candidates side by side.
      </p>
      <Link to="/candidates" className="text-sm text-blue-600 hover:underline">← Browse candidates</Link>
    </div>
  )

  if (notFound) return (
    <div className="space-y-2">
      <p className="text-slate-700">Candidate <code>{notFound}</code> not found.</p>
      <Link to="/candidates" className="text-sm text-blue-600 hover:underline">← Browse candidates</Link>
    </div>
  )

  if (!a || !b) return null

  const diff = computeDiff(a, b)

  return (
    <article className="space-y-8 pb-16">

      <Link to="/candidates" className="text-sm text-blue-600 hover:underline">← All candidates</Link>

      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Side-by-side comparison</h1>
        <div className="grid grid-cols-2 gap-4">
          <CandidateHeader candidate={a} accent="blue" />
          <CandidateHeader candidate={b} accent="purple" />
        </div>
      </header>

      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Skills</h2>

        {diff.sharedSkills.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-slate-500">
              Shared ({diff.sharedSkills.length})
            </p>
            <div className="flex flex-wrap gap-2">
              {diff.sharedSkills.map(s => (
                <span key={s.id} className="rounded bg-slate-100 px-2 py-1 text-xs text-slate-700">{s.name}</span>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-blue-600">
              Only {a.fullName.split(' ')[0]} ({diff.onlyInA.length})
            </p>
            {diff.onlyInA.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {diff.onlyInA.map(s => (
                  <span key={s.id} className="rounded bg-blue-100 px-2 py-1 text-xs text-blue-700">{s.name}</span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No unique skills</p>
            )}
          </div>
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-purple-600">
              Only {b.fullName.split(' ')[0]} ({diff.onlyInB.length})
            </p>
            {diff.onlyInB.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {diff.onlyInB.map(s => (
                  <span key={s.id} className="rounded bg-purple-100 px-2 py-1 text-xs text-purple-700">{s.name}</span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400">No unique skills</p>
            )}
          </div>
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Experience</h2>
        <div className="grid grid-cols-2 gap-4">
          <ExperienceColumn items={a.experience} />
          <ExperienceColumn items={b.experience} />
        </div>
      </section>

      {(a.education.length > 0 || b.education.length > 0) && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Education</h2>
          <div className="grid grid-cols-2 gap-4">
            <EducationColumn items={a.education} />
            <EducationColumn items={b.education} />
          </div>
        </section>
      )}

      {(a.certifications.length > 0 || b.certifications.length > 0) && (
        <section className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-slate-400">Certifications</h2>
          <div className="grid grid-cols-2 gap-4">
            <CertColumn items={a.certifications} />
            <CertColumn items={b.certifications} />
          </div>
        </section>
      )}

    </article>
  )
}
