import { useLayoutEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'

const MAX_LENGTH = 4000
const MAX_HEIGHT_PX = 200

interface ComposerProps {
  running: boolean
  canSend: boolean
  onSend: (text: string) => void
  onStop: () => void
}

export function Composer({ running, canSend, onSend, onStop }: ComposerProps) {
  const [draft, setDraft] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const trimmed = draft.trim()

  useLayoutEffect(() => {
    const element = textareaRef.current
    if (!element) return
    element.style.height = 'auto'
    element.style.height = `${Math.min(element.scrollHeight, MAX_HEIGHT_PX)}px`
  }, [draft])

  const submit = () => {
    if (!trimmed || !canSend || running) return
    onSend(trimmed)
    setDraft('')
  }

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form className="composer" onSubmit={onSubmit}>
      <textarea
        ref={textareaRef}
        className="composer__input"
        rows={1}
        value={draft}
        maxLength={MAX_LENGTH}
        placeholder={canSend ? 'Message the agent\u2026 (Enter to send, Shift+Enter for a new line)' : 'Waiting for the agent connection\u2026'}
        aria-label="Message"
        disabled={!canSend}
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={onKeyDown}
      />
      {running ? (
        <button type="button" className="composer__button composer__button--stop" onClick={onStop}>
          Stop
        </button>
      ) : (
        <button type="submit" className="composer__button" disabled={!canSend || !trimmed}>
          Send
        </button>
      )}
    </form>
  )
}
