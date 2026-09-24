import { cn } from '@/lib/utils'

// Child selectors instead of the typography plugin: one less dependency, and
// every color stays bound to a theme token.
export const MARKDOWN_CLASSES = cn(
  'space-y-3 text-sm leading-relaxed',
  '[&_strong]:font-semibold [&_a]:underline [&_a]:underline-offset-4',
  '[&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-1',
  '[&_h1]:font-semibold [&_h2]:font-semibold [&_h3]:font-semibold',
  '[&_table]:w-full [&_table]:border-collapse [&_table]:text-left [&_table]:text-xs',
  '[&_th]:border-b [&_th]:px-2 [&_th]:py-1.5 [&_th]:font-semibold [&_td]:border-b [&_td]:px-2 [&_td]:py-1.5 [&_td]:align-top',
  '[&_blockquote]:border-l-2 [&_blockquote]:pl-3 [&_blockquote]:text-muted-foreground',
)

const TABLE_ROW = /^\s*\|.*\|\s*$/
const SEPARATOR_ROW = /^\s*\|(\s*:?-{3,}:?\s*\|)+\s*$/

/**
 * Chunks split tables mid-way, so a chunk can start with pipe rows that have
 * no header separator — which GFM renders as literal text. Promote the first
 * row of each such block to a header so the rows still render as a table.
 */
export function repairTableFragments(markdown: string): string {
  const lines = markdown.split('\n')
  const output: string[] = []
  for (let i = 0; i < lines.length; i++) {
    output.push(lines[i])
    const startsBlock = TABLE_ROW.test(lines[i]) && (i === 0 || !TABLE_ROW.test(lines[i - 1]))
    if (startsBlock && !SEPARATOR_ROW.test(lines[i]) && !SEPARATOR_ROW.test(lines[i + 1] ?? '')) {
      const columns = lines[i].trim().slice(1, -1).split('|').length
      output.push(`|${' --- |'.repeat(columns)}`)
    }
  }
  return output.join('\n')
}
