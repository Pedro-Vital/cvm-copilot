import { useCallback, useEffect, useState } from 'react'
import { Trash2 } from 'lucide-react'
import { Link, Outlet, useNavigate, useParams } from 'react-router-dom'

import { DeleteThreadDialog } from '@/components/chat/DeleteThreadDialog'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import type { ChatLayoutContext } from '@/lib/chat-layout-context'
import { describeChatError } from '@/lib/chat-errors'
import type { Thread } from '@/lib/chat-types'
import { supabase } from '@/lib/supabase'

export function ChatLayout() {
  const navigate = useNavigate()
  const { threadId } = useParams()
  const [threads, setThreads] = useState<Thread[] | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [pendingDelete, setPendingDelete] = useState<Thread | null>(null)

  const refreshThreads = useCallback(() => {
    api
      .get<Thread[]>('/chat/threads')
      .then((rows) => {
        setThreads(rows)
        setError(null)
      })
      .catch(setError)
  }, [])

  useEffect(refreshThreads, [refreshThreads])

  const startThread = useCallback(
    async (prompt?: string) => {
      try {
        const thread = await api.post<Thread>('/chat/threads', { title: null })
        setThreads((prev) => [thread, ...(prev ?? [])])
        navigate(`/chat/${thread.id}`, { state: prompt ? { initialPrompt: prompt } : null })
      } catch (err) {
        setError(err as Error)
      }
    },
    [navigate],
  )

  const deleteThread = async (thread: Thread) => {
    await api.delete<void>(`/chat/threads/${thread.id}`)
    setThreads((prev) => prev?.filter((t) => t.id !== thread.id) ?? null)
    setPendingDelete(null)
    if (thread.id === threadId) navigate('/chat', { replace: true })
  }

  const context: ChatLayoutContext = { startThread, refreshThreads }

  return (
    <div className="flex h-svh">
      <aside className="flex w-64 shrink-0 flex-col border-r">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-2">
            <img src="/ipe-amarelo.png" alt="" className="size-6" />
            <h1 className="text-sm font-medium">CVM Copilot</h1>
          </div>
          <Button variant="outline" size="sm" onClick={() => supabase.auth.signOut()}>
            Sair
          </Button>
        </div>
        <div className="px-4 pb-2">
          <Button className="w-full" onClick={() => startThread()}>
            Nova conversa
          </Button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2">
          {error && (
            <div role="alert" className="flex flex-col gap-1 px-2 py-1.5 text-sm">
              <p className="font-medium text-destructive">{describeChatError(error).title}</p>
              <p className="text-muted-foreground">{describeChatError(error).message}</p>
              <button type="button" className="w-fit underline underline-offset-4" onClick={refreshThreads}>
                Tentar novamente
              </button>
            </div>
          )}
          {!threads && !error && <p className="px-2 text-sm text-muted-foreground">Carregando…</p>}
          {threads?.length === 0 && (
            <p className="px-2 text-sm text-muted-foreground">Nenhuma conversa ainda. Faça uma pergunta para começar.</p>
          )}
          {threads?.map((thread) => (
            <div
              key={thread.id}
              className={`group flex items-center rounded-md ${
                thread.id === threadId ? 'bg-muted font-medium' : 'hover:bg-muted/50'
              }`}
            >
              <Link to={`/chat/${thread.id}`} className="min-w-0 flex-1 truncate px-2 py-1.5 text-sm">
                {thread.title ?? 'Nova conversa'}
              </Link>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Excluir “${thread.title ?? 'Nova conversa'}”`}
                className="mr-1 shrink-0 text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-destructive focus-visible:opacity-100"
                onClick={() => setPendingDelete(thread)}
              >
                <Trash2 />
              </Button>
            </div>
          ))}
        </nav>
      </aside>
      <DeleteThreadDialog thread={pendingDelete} onCancel={() => setPendingDelete(null)} onConfirm={deleteThread} />
      <main className="flex min-w-0 flex-1 flex-col">
        <Outlet context={context} />
      </main>
    </div>
  )
}
