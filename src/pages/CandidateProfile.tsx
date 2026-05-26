import { useParams } from 'react-router-dom'

export default function CandidateProfile() {
  const { id } = useParams()
  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight">Candidate {id}</h1>
      <p className="mt-2 text-slate-500">
        Structured profile and original-CV link — arrives in commit 6.
      </p>
    </section>
  )
}
