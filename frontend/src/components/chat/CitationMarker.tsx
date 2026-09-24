import { cn } from '@/lib/utils'

interface CitationMarkerProps {
  index: number
  selected: boolean
  onSelect: () => void
}

export function CitationMarker({ index, selected, onSelect }: CitationMarkerProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-label={`Ver fonte ${index}`}
      className={cn(
        'mx-0.5 inline-flex h-4 min-w-4 -translate-y-0.5 items-center justify-center rounded px-1 align-baseline text-[0.65rem] font-semibold tabular-nums transition-colors',
        selected
          ? 'bg-primary text-primary-foreground'
          : 'bg-muted-foreground/15 text-foreground hover:bg-primary hover:text-primary-foreground',
      )}
    >
      {index}
    </button>
  )
}
