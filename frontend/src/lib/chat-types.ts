import type { UIMessage } from 'ai'

export interface Thread {
  id: string
  title: string | null
  createdAt: string
  updatedAt: string
}

export interface ThreadDetail extends Thread {
  messages: UIMessage[]
}
