import { DefaultChatTransport, type UIMessage } from 'ai'

import { env } from '@/lib/env'
import { supabase } from '@/lib/supabase'

export function createChatTransport(threadId: string) {
  return new DefaultChatTransport<UIMessage>({
    api: `${env.apiBaseUrl}/chat/stream`,
    body: { threadId },
    headers: async () => {
      const {
        data: { session },
      } = await supabase.auth.getSession()
      return session ? { Authorization: `Bearer ${session.access_token}` } : {}
    },
  })
}
