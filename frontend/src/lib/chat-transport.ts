import { DefaultChatTransport } from 'ai'

import type { ChatMessage } from '@/lib/chat-types'
import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

export function createChatTransport(threadId: string) {
  return new DefaultChatTransport<ChatMessage>({
    api: `${env.apiBaseUrl}/chat/stream`,
    body: { threadId },
    headers: async (): Promise<Record<string, string>> => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      return session ? { Authorization: `Bearer ${session.access_token}` } : {}
    },
  })
}
