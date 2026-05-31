import { useRef, useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { askChat } from '../lib/db'
import type { ChatResponse, ChatTurn } from '../lib/types'

type Message =
  | { role: 'user'; content: string }
  | { role: 'assistant'; content: string; data?: ChatResponse }

export default function Chat() {
  const { token } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  async function send() {
    const q = input.trim()
    if (!q || loading) return
    const history: ChatTurn[] = messages.map(m => ({ role: m.role, content: m.content }))
    setMessages(m => [...m, { role: 'user', content: q }])
    setInput('')
    setLoading(true)
    try {
      const res = await askChat(q, history, token!)
      setMessages(m => [...m, { role: 'assistant', content: res.answer || res.error || '…', data: res }])
    } catch (e: any) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'Sorry — I could not answer that. Try rephrasing your question.',
      }])
    } finally {
      setLoading(false)
      requestAnimationFrame(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }))
    }
  }

  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Ask Hellio</h1>
      <p className="text-slate-500 text-sm">
        Ask about candidates and positions in plain language. Every answer shows the SQL it ran.
      </p>

      <div className="space-y-3">
        {messages.map((m, i) =>
          m.role === 'user' ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-2xl rounded-lg bg-slate-900 px-4 py-2 text-sm text-white">{m.content}</div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className="max-w-2xl space-y-2">
                <div className="rounded-lg bg-white border border-slate-200 px-4 py-2 text-sm">{m.content}</div>
                {m.data && <RetrievalPanel data={m.data} />}
              </div>
            </div>
          ),
        )}
        {loading && <p className="text-slate-400 text-sm">Thinking…</p>}
        <div ref={endRef} />
      </div>

      <form onSubmit={e => { e.preventDefault(); send() }} className="flex gap-2">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="e.g. which positions have more than 2 candidates?"
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
        />
        <button type="submit" disabled={loading}
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">
          Ask
        </button>
      </form>
    </section>
  )
}

function RetrievalPanel({ data }: { data: ChatResponse }) {
  const [open, setOpen] = useState(false)
  const badge =
    data.status === 'success' ? 'text-emerald-700 bg-emerald-50'
    : data.status === 'unsafe' ? 'text-amber-700 bg-amber-50'
    : 'text-rose-700 bg-rose-50'
  return (
    <div className="rounded-md border border-slate-200 bg-slate-50 text-xs">
      <button onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-3 py-2 text-slate-600">
        <span>What was retrieved · {data.trace.rowCount} rows</span>
        <span className={`rounded px-1.5 py-0.5 ${badge}`}>{data.status}</span>
      </button>
      {open && (
        <div className="space-y-2 border-t border-slate-200 px-3 py-2">
          <div>
            <div className="font-medium text-slate-500">SQL</div>
            <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-900 p-2 text-slate-100">{data.sql || '—'}</pre>
          </div>
          {data.error && <div className="text-rose-700">{data.error}</div>}
          <div className="text-slate-500">columns: {data.trace.columns.join(', ') || '—'}</div>
          {data.trace.rows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="min-w-full border border-slate-200">
                <thead><tr>{data.trace.columns.map(c => (
                  <th key={c} className="border border-slate-200 bg-white px-2 py-1 text-left">{c}</th>
                ))}</tr></thead>
                <tbody>{data.trace.rows.slice(0, 20).map((r, i) => (
                  <tr key={i}>{data.trace.columns.map(c => (
                    <td key={c} className="border border-slate-200 px-2 py-1">{String((r as any)[c] ?? '')}</td>
                  ))}</tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
