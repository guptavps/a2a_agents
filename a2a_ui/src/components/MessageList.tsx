import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../state/types.ts'
import { MessageBubble } from './MessageBubble.tsx'

const STICK_THRESHOLD_PX = 80

export function MessageList({ messages }: { messages: ChatMessage[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const stickToBottom = useRef(true)

  const onScroll = () => {
    const element = containerRef.current
    if (element) {
      stickToBottom.current = element.scrollHeight - element.scrollTop - element.clientHeight < STICK_THRESHOLD_PX
    }
  }

  useEffect(() => {
    const element = containerRef.current
    if (element && stickToBottom.current) element.scrollTop = element.scrollHeight
  }, [messages])

  return (
    <div ref={containerRef} className="chat__body" role="log" aria-live="polite" onScroll={onScroll}>
      <div className="messages">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
      </div>
    </div>
  )
}
