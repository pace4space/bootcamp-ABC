const colors: Record<string, string> = {
  Waiting:   'bg-yellow-100 text-yellow-700',
  Rejected:  'bg-red-100 text-red-700',
  Screening: 'bg-blue-100 text-blue-700',
  Offer:     'bg-purple-100 text-purple-700',
  Hired:     'bg-green-100 text-green-700',
}

export default function AppStatusBadge({ status }: { status: string | null }) {
  if (!status) return <span className="text-xs text-slate-400">—</span>
  return (
    <span className={`rounded px-2 py-1 text-xs font-medium ${colors[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  )
}
