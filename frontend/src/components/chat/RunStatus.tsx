import { Loader2 } from 'lucide-react'

export function RunStatus({ message }: { message: string }) {
  return (
    <p aria-live="polite" className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 shrink-0 animate-spin" />
      {message}
    </p>
  )
}
