import { useChat } from '@ai-sdk/react'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

import { MessageInput } from '@/components/chat/MessageInput'
import { MessageList } from '@/components/chat/MessageList'
import { api } from '@/lib/api'
import { createChatTransport } from '@/lib/chat-transport'
import type { ThreadDetail } from '@/lib/chat-types'

export function ChatThread() {
  const { threadId } = useParams<{ threadId: string }>()
  if (!threadId) return null

  // Keying on threadId remounts the loader (and its state) on navigation
  // between threads, instead of resetting state inside an effect.
  return <ChatThreadLoader key={threadId} threadId={threadId} />
}

function ChatThreadLoader({ threadId }: { threadId: string }) {
  const [thread, setThread] = useState<ThreadDetail | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)

  useEffect(() => {
    api
      .get<ThreadDetail>(`/chat/threads/${threadId}`)
      .then(setThread)
      .catch(() => setLoadError('Não foi possível carregar esta conversa.'))
  }, [threadId])

  if (loadError) {
    return <div className="flex flex-1 items-center justify-center text-sm text-destructive">{loadError}</div>
  }

  if (!thread) {
    return <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">Carregando…</div>
  }

  // Remounts ChatThreadView (and its useChat instance) whenever the active
  // thread changes, so streamed state never leaks across threads.
  return <ChatThreadView key={thread.id} threadId={thread.id} initialMessages={thread.messages} />
}

interface ChatThreadViewProps {
  threadId: string
  initialMessages: ThreadDetail['messages']
}

function ChatThreadView({ threadId, initialMessages }: ChatThreadViewProps) {
  const { messages, sendMessage, status } = useChat({
    id: threadId,
    messages: initialMessages,
    transport: createChatTransport(threadId),
  })

  const isStreaming = status === 'submitted' || status === 'streaming'

  return (
    <>
      <MessageList messages={messages} isStreaming={isStreaming} />
      <MessageInput disabled={isStreaming} onSend={(text) => sendMessage({ text })} />
    </>
  )
}
