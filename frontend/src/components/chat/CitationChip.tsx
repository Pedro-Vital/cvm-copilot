import type { Citation } from '@/lib/chat-types'
import { filingLabel, locationLabel } from '@/lib/citations'
import { cn } from '@/lib/utils'

interface CitationChipProps {
  citation: Citation
  selected: boolean
  onSelect: () => void
}

export function CitationChip({ citation, selected, onSelect }: CitationChipProps) {
  const location = locationLabel(citation)

  return (
    <button
      type="button"
      onClick={onSelect}
      title={[citation.companyName, filingLabel(citation), location].filter(Boolean).join(' · ')}
      className={cn(
        'inline-flex max-w-full items-center gap-1.5 rounded-full border py-0.5 pr-3 pl-0.5 text-left text-xs transition-colors',
        selected
          ? 'border-primary bg-primary/5 text-foreground'
          : 'bg-background text-muted-foreground hover:border-foreground/40 hover:text-foreground',
      )}
    >
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-[0.65rem] font-semibold text-primary-foreground tabular-nums">
        {citation.citationIndex}
      </span>
      <span className="shrink-0 font-medium text-foreground">{filingLabel(citation)}</span>
      {location && <span className="truncate">{location}</span>}
    </button>
  )
}
