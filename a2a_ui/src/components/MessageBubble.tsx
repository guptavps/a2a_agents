import ReactMarkdown from 'react-markdown'
import type { AgentMessage, ChatMessage } from '../state/types.ts'
import { ReasoningPanel } from './ReasoningPanel.tsx'

// react-markdown does not render raw HTML; links are the only extra surface, so open them safely.
const markdownComponents = {
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

function AgentTurn({ turn }: { turn: AgentMessage }) {
  const running = turn.status === 'running'
  const showReasoning = running || turn.steps.length > 0
  const finishedWithoutText = turn.status === 'done' && !turn.answer

  return (
    <article className="message message--agent" aria-busy={running}>
      {showReasoning && <ReasoningPanel key={running ? 'live' : 'settled'} steps={turn.steps} running={running} />}
      {turn.answer && (
        <div className="answer">
          <ReactMarkdown components={markdownComponents}>{turn.answer}</ReactMarkdown>
        </div>
      )}
      {turn.status === 'error' && (
        <p className="turn-note turn-note--error" role="alert">
          {turn.error}
        </p>
      )}
      {turn.status === 'canceled' && <p className="turn-note">Stopped.</p>}
      {finishedWithoutText && <p className="turn-note">The agent finished without a text answer.</p>}
    </article>
  )
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  if (message.role === 'user') {
    return (
      <article className="message message--user">
        <p>{message.text}</p>
      </article>
    )
  }
  return <AgentTurn turn={message} />
}
