import type { ChatMessage, Citation } from '@/lib/chat-types'

export function messageText(message: ChatMessage): string {
  return message.parts.map((part) => (part.type === 'text' ? part.text : '')).join('')
}

export function messageCitations(message: ChatMessage): Citation[] {
  return message.parts
    .flatMap((part) => (part.type === 'data-citation' ? [part.data] : []))
    .sort((a, b) => a.citationIndex - b.citationIndex)
}

/** "VALE3 · DFP 2023" */
export function filingLabel(citation: Pick<Citation, 'ticker' | 'form' | 'fiscalYear'>): string {
  return `${citation.ticker} · ${citation.form} ${citation.fiscalYear}`
}

/** "p. 91 · Notas Explicativas — Informações por segmento", or null when neither is known. */
export function locationLabel(location: Pick<Citation, 'page' | 'section'>): string | null {
  const bits = [location.page !== null ? `p. ${location.page}` : null, location.section].filter(Boolean)
  return bits.length > 0 ? bits.join(' · ') : null
}

const DATE_FORMAT = new Intl.DateTimeFormat('pt-BR', { timeZone: 'UTC' })

/** "2023-12-31" → "31/12/2023". UTC so a date-only value never shifts a day. */
export function formatReferencePeriod(isoDate: string): string {
  return DATE_FORMAT.format(new Date(isoDate))
}
