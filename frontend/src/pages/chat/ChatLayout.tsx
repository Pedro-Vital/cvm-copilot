import { useEffect, useState } from 'react'
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { Thread } from '@/lib/chat-types'
import { supabase } from '@/lib/supabase'

export function ChatLayout() {
  const navigate = useNavigate()
  const { threadId } = useParams()
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api
      .get<Thread[]>('/chat/threads')
      .then(setThreads)
      .finally(() => setLoading(false))
  }, [])

  async function handleNewChat() {
    const thread = await api.post<Thread>('/chat/threads', { title: null })
    setThreads((prev) => [thread, ...prev])
    navigate(`/chat/${thread.id}`)
  }

  return (
    <div className="flex h-svh">
      <aside className="flex w-64 shrink-0 flex-col border-r">
        <div className="flex items-center justify-between p-4">
          <h1 className="text-sm font-medium">CVM Copilot</h1>
          <Button variant="outline" size="sm" onClick={() => supabase.auth.signOut()}>
            Sair
          </Button>
        </div>
        <div className="px-4 pb-2">
          <Button className="w-full" onClick={handleNewChat}>
            Nova conversa
          </Button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2">
          {loading && <p className="px-2 text-sm text-muted-foreground">Carregando…</p>}
          {threads.map((thread) => (
            <Link
              key={thread.id}
              to={`/chat/${thread.id}`}
              className={`block truncate rounded-md px-2 py-1.5 text-sm ${
                thread.id === threadId ? 'bg-muted font-medium' : 'hover:bg-muted/50'
              }`}
            >
              {thread.title ?? 'Nova conversa'}
            </Link>
          ))}
        </nav>
      </aside>
      <main className="flex flex-1 flex-col">
        <Outlet />
      </main>
    </div>
  )
}
