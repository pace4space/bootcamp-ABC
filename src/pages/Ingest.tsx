import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

type IngestResult = {
  status: string
  entityId?: string
  runId: number
  inputTokens: number
  outputTokens: number
  warnings: string[]
  errors: string[]
}

export default function Ingest() {
  const { token, user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<IngestResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (user && !['admin', 'recruiter'].includes(user.role)) {
    return (
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">Upload CV</h1>
        <p className="text-slate-500">Only admins and recruiters can upload CVs.</p>
      </div>
    )
  }

  async function handleUpload() {
    if (!file || !token) return
    setLoading(true)
    setResult(null)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/ingest/cv', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? 'Upload failed')
        return
      }
      setResult(data)
    } catch {
      setError('Network error — is the API running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Upload CV</h1>

      <div className="max-w-lg space-y-4 rounded border border-slate-200 bg-white p-6">
        <div>
          <label htmlFor="cv-file" className="block text-sm font-medium text-slate-700">
            CV file (PDF or DOCX)
          </label>
          <input
            id="cv-file"
            type="file"
            accept=".pdf,.docx"
            onChange={e => { setFile(e.target.files?.[0] ?? null); setResult(null); setError(null) }}
            className="mt-1 block w-full text-sm text-slate-600 file:mr-4 file:rounded file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
          />
        </div>

        <button
          onClick={handleUpload}
          disabled={!file || loading}
          className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-40"
        >
          {loading ? 'Extracting…' : 'Upload & Extract'}
        </button>
      </div>

      {error && (
        <div className="max-w-lg rounded border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      {result && (
        <div className="max-w-lg space-y-3 rounded border border-slate-200 bg-white p-6">
          <div className="flex items-center gap-2">
            <span className={`inline-block rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide ${
              result.status === 'success' ? 'bg-green-100 text-green-700' :
              result.status === 'partial' ? 'bg-yellow-100 text-yellow-700' :
              'bg-red-100 text-red-700'
            }`}>
              {result.status}
            </span>
            {result.entityId && (
              <Link to={`/candidates/${result.entityId}`} className="text-sm text-indigo-600 hover:underline">
                View candidate →
              </Link>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
            <dt className="text-slate-500">Run ID</dt>
            <dd className="text-slate-900">{result.runId}</dd>
            <dt className="text-slate-500">Input tokens</dt>
            <dd className="text-slate-900">{result.inputTokens.toLocaleString()}</dd>
            <dt className="text-slate-500">Output tokens</dt>
            <dd className="text-slate-900">{result.outputTokens.toLocaleString()}</dd>
          </dl>

          {result.warnings.length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-yellow-600">Warnings</p>
              <ul className="mt-1 space-y-0.5">
                {result.warnings.map((w, i) => <li key={i} className="text-sm text-slate-700">{w}</li>)}
              </ul>
            </div>
          )}

          {result.errors.length > 0 && (
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-red-600">Errors</p>
              <ul className="mt-1 space-y-0.5">
                {result.errors.map((e, i) => <li key={i} className="text-sm text-slate-700">{e}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
