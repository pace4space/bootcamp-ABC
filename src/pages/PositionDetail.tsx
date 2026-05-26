import { useParams } from 'react-router-dom'

export default function PositionDetail() {
  const { id } = useParams()
  return (
    <section>
      <h1 className="text-2xl font-semibold tracking-tight">Position {id}</h1>
      <p className="mt-2 text-slate-500">
        Description and current candidates — arrives in commit 7.
      </p>
    </section>
  )
}
