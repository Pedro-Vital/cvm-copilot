import { useOutletContext } from 'react-router-dom'

/** What ChatLayout shares with the routes rendered in its <Outlet />. */
export interface ChatLayoutContext {
  /** Creates a thread and opens it, sending `prompt` as its first question when given. */
  startThread: (prompt?: string) => Promise<void>
  refreshThreads: () => void
}

export function useChatLayout(): ChatLayoutContext {
  return useOutletContext<ChatLayoutContext>()
}
