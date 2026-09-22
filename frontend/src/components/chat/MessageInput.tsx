import { type FormEvent, useState } from 'react'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface MessageInputProps {
  onSend: (text: string) => void
  disabled: boolean
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [text, setText] = useState('')

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText('')
  }

  return (
    <form className="flex gap-2 border-t p-4" onSubmit={handleSubmit}>
      <Input
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder="Pergunte sobre uma DFP…"
        disabled={disabled}
        autoFocus
      />
      <Button type="submit" disabled={disabled || !text.trim()}>
        Enviar
      </Button>
    </form>
  )
}
