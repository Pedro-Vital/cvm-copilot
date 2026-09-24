import { useMemo } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { CitationMarker } from '@/components/chat/CitationMarker'
import type { Citation } from '@/lib/chat-types'
import { MARKDOWN_CLASSES } from '@/lib/markdown'

const CITATION_HREF = '#citation-'

/** Turns each `[n]` that has a citation into a link the `a` renderer swaps for a marker button. */
function linkCitationMarkers(text: string, indices: Set<number>): string {
  return text.replace(/\[(\d+)\]/g, (marker, digits: string) =>
    indices.has(Number(digits)) ? `[${marker}](${CITATION_HREF}${digits})` : marker,
  )
}

interface AnswerMarkdownProps {
  text: string
  citations: Citation[]
  isSelected: (citation: Citation) => boolean
  onSelectCitation: (citation: Citation) => void
}

export function AnswerMarkdown({ text, citations, isSelected, onSelectCitation }: AnswerMarkdownProps) {
  const source = useMemo(
    () => linkCitationMarkers(text, new Set(citations.map((citation) => citation.citationIndex))),
    [text, citations],
  )

  const components: Components = {
    a({ href, children }) {
      const citation = href?.startsWith(CITATION_HREF)
        ? citations.find((c) => c.citationIndex === Number(href.slice(CITATION_HREF.length)))
        : undefined
      if (citation) {
        return (
          <CitationMarker
            index={citation.citationIndex}
            selected={isSelected(citation)}
            onSelect={() => onSelectCitation(citation)}
          />
        )
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      )
    },
    table({ children }) {
      return (
        <div className="overflow-x-auto">
          <table>{children}</table>
        </div>
      )
    },
  }

  return (
    <div className={MARKDOWN_CLASSES}>
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {source}
      </Markdown>
    </div>
  )
}
