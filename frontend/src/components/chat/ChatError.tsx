import { AlertTriangle } from 'lucide-react'

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { describeChatError } from '@/lib/chat-errors'
import { supabase } from '@/lib/supabase'

interface ChatErrorProps {
  error: Error
  onRetry?: () => void
}

export function ChatError({ error, onRetry }: ChatErrorProps) {
  const { title, message, sessionExpired } = describeChatError(error)

  return (
    <Alert variant="destructive">
      <AlertTriangle />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex flex-col items-start gap-2">
        <span>{message}</span>
        {/* Signing out lets ProtectedRoute send the analyst to the login page. */}
        {sessionExpired ? (
          <Button size="sm" variant="outline" onClick={() => supabase.auth.signOut()}>
            Entrar novamente
          </Button>
        ) : (
          onRetry && (
            <Button size="sm" variant="outline" onClick={onRetry}>
              Tentar novamente
            </Button>
          )
        )}
      </AlertDescription>
    </Alert>
  )
}
