import { useChat } from '@ai-sdk/react'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'

import { ChatError } from '@/components/chat/ChatError'
import { MessageInput } from '@/components/chat/MessageInput'
import { MessageList } from '@/components/chat/MessageList'
import { SourcePassagePanel } from '@/components/chat/SourcePassagePanel'
import { RunStatus } from '@/components/chat/RunStatus'
import { api } from '@/lib/api'
import { useChatLayout } from '@/lib/chat-layout-context'
import { createChatTransport } from '@/lib/chat-transport'
import type { ChatMessage, Citation, ThreadDetail } from '@/lib/chat-types'
import { messageText } from '@/lib/citations'

export function ChatThread() {
  const { threadId } = useParams<{ threadId: string }>()
  if (!threadId) return null

  // Keying on threadId remounts the loader (and its state) on navigation
  // between threads, instead of resetting state inside an effect.
  return <ChatThreadLoader key={threadId} threadId={threadId} />
}

function ChatThreadLoader({ threadId }: { threadId: string }) {
  const [thread, setThread] = useState<ThreadDetail | null>(null)
  const [loadError, setLoadError] = useState<Error | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    api.get<ThreadDetail>(`/chat/threads/${threadId}`).then(setThread).catch(setLoadError)
  }, [threadId, attempt])

  if (loadError) {
    return (
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <ChatError
            error={loadError}
            onRetry={() => {
              setLoadError(null)
              setAttempt((n) => n + 1)
            }}
          />
        </div>
      </div>
    )
  }

  if (!thread) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <RunStatus message="Carregando a conversa…" />
      </div>
    )
  }

  // Remounts ChatThreadView (and its useChat instance) whenever the active
  // thread changes, so streamed state never leaks across threads.
  return <ChatThreadView key={thread.id} threadId={thread.id} initialMessages={thread.messages} />
}

interface ChatThreadViewProps {
  threadId: string
  initialMessages: ChatMessage[]
}

function ChatThreadView({ threadId, initialMessages }: ChatThreadViewProps) {
  const { refreshThreads } = useChatLayout()
  const location = useLocation()
  const navigate = useNavigate()
  const [runStatus, setRunStatus] = useState<string | null>(null)
  const [selected, setSelected] = useState<Citation | null>(null)
  // Kept apart from `selected` so the panel keeps its content while it animates closed.
  const [panelOpen, setPanelOpen] = useState(false)

  const { messages, sendMessage, regenerate, status, error } = useChat<ChatMessage>({
    id: threadId,
    messages: initialMessages,
    transport: createChatTransport(threadId),
    onData: (part) => {
      if (part.type === 'data-status') setRunStatus(part.data.message)
    },
    // The turn bumped the thread's updated_at, so the sidebar order changed.
    onFinish: () => refreshThreads(),
  })

  const isBusy = status === 'submitted' || status === 'streaming'
  const last = messages.at(-1)
  const streamingMessageId = isBusy && last?.role === 'assistant' ? last.id : null
  // The answer is revealed only after grounding validation, so the status
  // line covers the whole agent run and disappears once text starts arriving.
  const revealing = streamingMessageId !== null && last !== undefined && messageText(last).length > 0
  const shownStatus = isBusy && !revealing ? (runStatus ?? 'Enviando a pergunta…') : null

  function send(text: string) {
    setRunStatus(null)
    void sendMessage({ text })
  }

  function retry() {
    setRunStatus(null)
    void regenerate()
  }

  // A question picked on the empty page arrives as router state; send it once
  // and clear it so a reload doesn't send it again.
  const initialPrompt = (location.state as { initialPrompt?: string } | null)?.initialPrompt
  const sentInitialPrompt = useRef(false)
  useEffect(() => {
    if (!initialPrompt || sentInitialPrompt.current) return
    sentInitialPrompt.current = true
    navigate(location.pathname, { replace: true, state: null })
    void sendMessage({ text: initialPrompt })
  }, [initialPrompt, location.pathname, navigate, sendMessage])

  return (
    <>
      <MessageList
        messages={messages}
        runStatus={shownStatus}
        streamingMessageId={streamingMessageId}
        isSelected={(citation) =>
          panelOpen && selected?.chunkId === citation.chunkId && selected.citationIndex === citation.citationIndex
        }
        onSelectCitation={(citation) => {
          setSelected(citation)
          setPanelOpen(true)
        }}
        onPickExample={send}
        footer={error && !isBusy ? <ChatError error={error} onRetry={retry} /> : null}
      />
      <MessageInput disabled={isBusy} onSend={send} />
      <SourcePassagePanel citation={selected} open={panelOpen} onOpenChange={setPanelOpen} />
    </>
  )
}
