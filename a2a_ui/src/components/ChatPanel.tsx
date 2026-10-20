import type { ConnectionState } from '../hooks/useAgentConnection.ts'
import { isRunning } from '../state/chatReducer.ts'
import type { Conversation } from '../state/types.ts'
import { Composer } from './Composer.tsx'
import { MessageList } from './MessageList.tsx'

interface ChatPanelProps {
  conversation: Conversation
  connection: ConnectionState
  onRetry: () => void
  onSend: (text: string) => void
  onStop: () => void
}

export function ChatPanel({ conversation, connection, onRetry, onSend, onStop }: ChatPanelProps) {
  const running = isRunning(conversation)

  return (
    <main className="chat">
      <header className="chat__header">
        <h1 className="chat__title">{conversation.title}</h1>
      </header>
      {connection.status === 'error' && (
        <div className="banner banner--error" role="alert">
          {connection.message}{' '}
          <button type="button" className="link-button" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}
      {conversation.messages.length === 0 ? (
        <div className="chat__body">
          <div className="empty-state">
            <h2>Ask the agent anything</h2>
            <p>Messages, live reasoning and answers will appear here.</p>
          </div>
        </div>
      ) : (
        <MessageList key={`messages-${conversation.id}`} messages={conversation.messages} />
      )}
      <Composer
        key={`composer-${conversation.id}`}
        running={running}
        canSend={connection.status === 'ready'}
        onSend={onSend}
        onStop={onStop}
      />
    </main>
  )
}
