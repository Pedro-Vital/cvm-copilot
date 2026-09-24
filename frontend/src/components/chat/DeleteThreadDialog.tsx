import { useState } from 'react'

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { describeChatError } from '@/lib/chat-errors'
import type { Thread } from '@/lib/chat-types'

type Props = {
  thread: Thread | null
  onCancel: () => void
  onConfirm: (thread: Thread) => Promise<void>
}

export function DeleteThreadDialog({ thread, onCancel, onConfirm }: Props) {
  const [deleting, setDeleting] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const close = () => {
    setError(null)
    onCancel()
  }

  const confirm = async () => {
    if (!thread) return
    setDeleting(true)
    setError(null)
    try {
      await onConfirm(thread)
    } catch (err) {
      setError(err as Error)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <AlertDialog open={thread !== null} onOpenChange={(open) => !open && !deleting && close()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir conversa?</AlertDialogTitle>
          <AlertDialogDescription>
            “{thread?.title ?? 'Nova conversa'}” e todas as suas mensagens serão excluídas. Essa ação não pode ser
            desfeita.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {describeChatError(error).message}
          </p>
        )}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={deleting}>Cancelar</AlertDialogCancel>
          <Button variant="destructive" disabled={deleting} onClick={confirm}>
            {deleting ? 'Excluindo…' : 'Excluir'}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
