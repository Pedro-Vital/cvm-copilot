import { type ReactNode, useEffect, useRef } from 'react'

import { AssistantMessage } from '@/components/chat/AssistantMessage'
import { ExampleQuestions } from '@/components/chat/ExampleQuestions'
import { RunStatus } from '@/components/chat/RunStatus'
import type { ChatMessage, Citation } from '@/lib/chat-types'
import { messageText } from '@/lib/citations'

interface MessageListProps {
  messages: ChatMessage[]
  /** Progress line while the assistant works; null when idle or once the answer is being revealed. */
  runStatus: string | null
  streamingMessageId: string | null
  isSelected: (citation: Citation) => boolean
  onSelectCitation: (citation: Citation) => void
  onPickExample: (question: string) => void
  footer?: ReactNode
}

export function MessageList({
  messages,
  runStatus,
  streamingMessageId,
  isSelected,
  onSelectCitation,
  onPickExample,
  footer,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, runStatus, footer])

  if (messages.length === 0 && !runStatus) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto p-6 text-center">
        <div className="flex flex-col gap-1">
          <h2 className="text-lg font-semibold">Pergunte sobre as DFPs</h2>
          <p className="text-sm text-muted-foreground">
            Itaú, Magazine Luiza, Suzano, Vale e WEG, exercícios de 2021 a 2025. Toda resposta cita os trechos de onde
            veio.
          </p>
        </div>
        <ExampleQuestions onPick={onPickExample} />
        {footer}
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
        {messages.map((message) =>
          message.role === 'user' ? (
            <div
              key={message.id}
              className="ml-auto max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm whitespace-pre-wrap text-primary-foreground"
            >
              {messageText(message)}
            </div>
          ) : (
            <AssistantMessage
              key={message.id}
              message={message}
              isStreaming={message.id === streamingMessageId}
              isSelected={isSelected}
              onSelectCitation={onSelectCitation}
            />
          ),
        )}
        {runStatus && <RunStatus message={runStatus} />}
        {footer}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
