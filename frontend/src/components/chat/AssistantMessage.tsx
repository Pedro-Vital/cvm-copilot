import { SearchX } from 'lucide-react'

import { AnswerMarkdown } from '@/components/chat/AnswerMarkdown'
import { CitationChip } from '@/components/chat/CitationChip'
import type { ChatMessage, Citation } from '@/lib/chat-types'
import { messageCitations, messageText } from '@/lib/citations'

interface AssistantMessageProps {
  message: ChatMessage
  isStreaming: boolean
  isSelected: (citation: Citation) => boolean
  onSelectCitation: (citation: Citation) => void
}

export function AssistantMessage({ message, isStreaming, isSelected, onSelectCitation }: AssistantMessageProps) {
  const text = messageText(message)
  const citations = messageCitations(message)
  // The grounding validator rejects any answer without citations unless it is
  // flagged insufficient_evidence, so a finished answer with none is exactly
  // the "corpus doesn't support this" case. Citation parts arrive after the
  // text, so wait for the stream to end before judging.
  const noEvidence = !isStreaming && text && citations.length === 0

  return (
    <div className="flex flex-col gap-3">
      <AnswerMarkdown text={text} citations={citations} isSelected={isSelected} onSelectCitation={onSelectCitation} />

      {noEvidence && (
        <p className="flex items-center gap-2 rounded-lg border border-dashed px-3 py-2 text-xs text-muted-foreground">
          <SearchX className="size-3.5 shrink-0" />
          Nenhum trecho das DFPs sustenta uma resposta — nada foi citado.
        </p>
      )}

      {citations.length > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-xs font-medium text-muted-foreground">Fontes</p>
          <div className="flex flex-wrap gap-1.5">
            {citations.map((citation) => (
              <CitationChip
                key={citation.citationIndex}
                citation={citation}
                selected={isSelected(citation)}
                onSelect={() => onSelectCitation(citation)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
