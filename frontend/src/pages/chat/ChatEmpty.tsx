import { useState } from 'react'

import { ExampleQuestions } from '@/components/chat/ExampleQuestions'
import { useChatLayout } from '@/lib/chat-layout-context'

export function ChatEmpty() {
  const { startThread } = useChatLayout()
  const [starting, setStarting] = useState(false)

  async function handlePick(question: string) {
    setStarting(true)
    await startThread(question)
    setStarting(false)
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto p-6 text-center">
      <div className="flex flex-col gap-1">
        <h2 className="text-xl font-semibold">Pesquise nas DFPs com fontes verificáveis</h2>
        <p className="max-w-lg text-sm text-muted-foreground">
          Faça perguntas sobre as demonstrações financeiras de Itaú, Magazine Luiza, Suzano, Vale e WEG (2021–2025).
          Cada afirmação traz a citação do trecho de onde veio — clique nela para conferir.
        </p>
      </div>
      <ExampleQuestions onPick={handlePick} disabled={starting} />
    </div>
  )
}
