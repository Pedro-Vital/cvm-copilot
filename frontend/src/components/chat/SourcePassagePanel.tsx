import { ExternalLink, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { Badge } from '@/components/ui/badge'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { api } from '@/lib/api'
import type { Citation, SourceChunk, SourceContext } from '@/lib/chat-types'
import { describeChatError } from '@/lib/chat-errors'
import { filingLabel, formatReferencePeriod, locationLabel } from '@/lib/citations'
import { MARKDOWN_CLASSES, repairTableFragments } from '@/lib/markdown'
import { cn } from '@/lib/utils'

interface SourcePassagePanelProps {
  citation: Citation | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SourcePassagePanel({ citation, open, onOpenChange }: SourcePassagePanelProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 data-[side=right]:w-full data-[side=right]:sm:max-w-2xl">
        {/* Keyed so switching citations remounts the loader instead of resetting state in an effect. */}
        {citation && <SourcePassage key={`${citation.chunkId}:${citation.citationIndex}`} citation={citation} />}
      </SheetContent>
    </Sheet>
  )
}

function SourcePassage({ citation }: { citation: Citation }) {
  const [context, setContext] = useState<SourceContext | null>(null)
  const [error, setError] = useState<string | null>(null)
  const location = locationLabel(citation)

  useEffect(() => {
    api
      .get<SourceContext>(`/sources/${citation.chunkId}?radius=1`)
      .then(setContext)
      .catch((err: Error) => setError(describeChatError(err).message))
  }, [citation.chunkId])

  return (
    <>
      <SheetHeader className="gap-2 border-b pr-12">
        <SheetTitle className="flex items-center gap-2">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md bg-primary text-xs font-semibold text-primary-foreground tabular-nums">
            {citation.citationIndex}
          </span>
          {citation.companyName}
        </SheetTitle>
        <SheetDescription className="sr-only">Trecho da DFP que sustenta a citação {citation.citationIndex}</SheetDescription>
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="secondary">{filingLabel(citation)}</Badge>
          <Badge variant="outline">Exercício encerrado em {formatReferencePeriod(citation.referencePeriod)}</Badge>
          {location && <Badge variant="outline">{location}</Badge>}
        </div>
        <a
          href={citation.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex w-fit items-center gap-1 text-xs font-medium underline underline-offset-4"
        >
          Abrir a DFP original na CVM
          <ExternalLink className="size-3" />
        </a>
      </SheetHeader>

      <div className="flex flex-1 flex-col gap-6 overflow-y-auto p-4">
        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Trecho citado</h3>
          <blockquote className="border-l-4 border-primary bg-muted/50 px-3 py-2 font-mono text-xs leading-relaxed break-words whitespace-pre-wrap">
            {citation.excerpt}
          </blockquote>
          <p className="text-xs text-muted-foreground">
            Verificado antes da resposta ser exibida: este texto aparece literalmente no trecho destacado abaixo.
          </p>
        </section>

        <section className="flex flex-col gap-2">
          <h3 className="text-xs font-medium tracking-wide text-muted-foreground uppercase">Contexto no documento</h3>
          {error && (
            <p role="alert" className="text-sm text-destructive">
              Não foi possível carregar o contexto: {error}
            </p>
          )}
          {!context && !error && (
            <p className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" />
              Carregando o trecho…
            </p>
          )}
          {context?.chunks.map((chunk) => <SourceChunkCard key={chunk.chunkId} chunk={chunk} />)}
        </section>
      </div>
    </>
  )
}

function SourceChunkCard({ chunk }: { chunk: SourceChunk }) {
  const location = locationLabel(chunk)

  return (
    <article
      className={cn('flex flex-col gap-2 rounded-lg border p-3', chunk.isAnchor ? 'border-primary bg-primary/5' : 'opacity-70')}
    >
      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        {chunk.isAnchor && <Badge>Trecho da citação</Badge>}
        {location && <span>{location}</span>}
      </div>
      <div className={cn(MARKDOWN_CLASSES, 'overflow-x-auto text-xs')}>
        <Markdown remarkPlugins={[remarkGfm]}>{repairTableFragments(chunk.content)}</Markdown>
      </div>
    </article>
  )
}
