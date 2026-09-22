import type { UIMessage } from 'ai'

interface MessageListProps {
  messages: UIMessage[]
  isStreaming: boolean
}

export function MessageList({ messages, isStreaming }: MessageListProps) {
  return (
    <div className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`max-w-[75%] rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
            message.role === 'user' ? 'ml-auto bg-primary text-primary-foreground' : 'bg-muted'
          }`}
        >
          {message.parts.map((part, index) => (part.type === 'text' ? <span key={index}>{part.text}</span> : null))}
        </div>
      ))}
      {isStreaming && <p className="text-sm text-muted-foreground">Respondendo…</p>}
    </div>
  )
}
