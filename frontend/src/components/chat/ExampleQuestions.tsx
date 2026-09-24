import { EXAMPLE_QUESTIONS } from '@/lib/example-questions'

interface ExampleQuestionsProps {
  onPick: (question: string) => void
  disabled?: boolean
}

export function ExampleQuestions({ onPick, disabled }: ExampleQuestionsProps) {
  return (
    <div className="grid w-full max-w-2xl gap-2 sm:grid-cols-2">
      {EXAMPLE_QUESTIONS.map((question) => (
        <button
          key={question}
          type="button"
          disabled={disabled}
          onClick={() => onPick(question)}
          className="rounded-lg border px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:border-foreground/40 hover:text-foreground disabled:opacity-50"
        >
          {question}
        </button>
      ))}
    </div>
  )
}
