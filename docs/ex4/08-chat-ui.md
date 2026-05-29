# Ex4 — Segment 08: Chat UI

**Depends on:** 07 (`POST /api/chat`). **Blocks:** the live demo (09).

## Goal

A `/chat` page with multi-turn Q&A and a per-answer **"What was retrieved"** panel (SQL + row count
+ columns + rows). The panel is the point: it makes the SQL-RAG loop legible to a human and proves
the answer is grounded. All styling is Tailwind v4, matching the existing slate palette. The data
call goes through the `lib/db.ts` seam (never `fetch` directly in the component).

## Step A — `src/lib/types.ts` (append chat types)

```ts
// ---------------------------------------------------------------------------
// Chat (Ex4 — SQL-RAG)
// ---------------------------------------------------------------------------
export type ChatRole = 'user' | 'assistant'
export type ChatTurn = { role: ChatRole; content: string }

export type ChatTrace = {
  rowCount: number
  columns: string[]
  rows: Record<string, unknown>[]
  promptVersion?: string
}

export type ChatResponse = {
  answer: string
  sql: string
  status: 'success' | 'unsafe' | 'sql_error' | 'llm_error'
  model: string
  runId: number
  trace: ChatTrace
  error?: string | null
  suggestion?: string | null
}
```

## Step B — `src/lib/db.ts` (append, same `apiFetch` seam)

```ts
import type { /* …existing… */ ChatTurn, ChatResponse } from './types'

export async function askChat(
  question: string,
  history: ChatTurn[],
  token: string,
): Promise<ChatResponse> {
  return (await apiFetch('/chat', token, {
    method: 'POST',
    body: JSON.stringify({ question, history }),
  })).json()
}
```

Note: `apiFetch` throws on non-2xx (it attaches `.status`). A 422 (LLM_ERROR) will throw; the page
catches it and renders an error bubble. `success`/`unsafe`/`sql_error` return 200 → normal path,
the page branches on `response.status`.

## Step C — `src/pages/Chat.tsx`

```tsx
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
```

## Step D — `src/App.tsx` (add route inside the Layout group)

```tsx
import Chat from './pages/Chat'
// …inside <Route element={<Layout />}> …
<Route path="chat" element={<Chat />} />
```

## Step E — `src/components/Layout.tsx` (add nav link)

```tsx
<NavLink to="/chat" className={linkClass}>Ask</NavLink>
```
(Place it after the Compare link.)

## Design notes
- **History is rebuilt from `messages` on each send** (before appending the new user turn) and sent
  to the backend — multi-turn context. The backend uses it as conversation entries (06).
- **The retrieval panel is collapsed by default**; expanding shows SQL, columns, and up to 20 rows.
  This is the "show what was retrieved" requirement and the grounding proof in one component.
- **No new dependency**, no context needed — chat is page-local state. `useAuth()` supplies the token;
  the call goes through the `lib/db.ts` seam like every other read.
- Status badge color encodes `success`/`unsafe`/`sql_error` so a rejected or failed query is visible.

## Verification
- `npm run build` and `tsc -b` clean.
- `npm run dev` → log in → `/chat` (nav "Ask") → ask the four demo questions → each answer shows a
  collapsible panel with SQL + rows; a follow-up like "which of those are senior?" carries context.
