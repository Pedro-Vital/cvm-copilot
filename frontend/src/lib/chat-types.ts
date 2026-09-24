import type { UIMessage } from 'ai'

export interface Thread {
  id: string
  title: string | null
  createdAt: string
  updatedAt: string
}

/** Mirrors the backend's `data-citation` part (app/chat/messages.py `citation_parts`). */
export interface Citation {
  citationIndex: number
  chunkId: string
  documentId: string
  excerpt: string
  ticker: string
  companyName: string
  form: string
  fiscalYear: number
  referencePeriod: string
  page: number | null
  section: string | null
  sourceUrl: string
}

/** Custom data parts streamed by /chat/stream. `status` is transient: it reaches onData but isn't kept on the message. */
// A type alias, not an interface: UIMessage requires a Record-compatible type.
export type ChatDataParts = {
  citation: Citation
  status: { message: string }
}

export type ChatMessage = UIMessage<unknown, ChatDataParts>

export interface ThreadDetail extends Thread {
  messages: ChatMessage[]
}

/** GET /sources/{chunkId}: the cited chunk plus its neighbors, in document order. */
export interface SourceContext {
  chunkId: string
  ticker: string
  companyName: string
  form: string
  fiscalYear: number
  referencePeriod: string
  sourceUrl: string
  chunks: SourceChunk[]
}

export interface SourceChunk {
  chunkId: string
  chunkIndex: number
  page: number | null
  section: string | null
  content: string
  isAnchor: boolean
}
