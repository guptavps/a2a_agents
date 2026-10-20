import type { ConnectionState } from '../hooks/useAgentConnection.ts'
import type { Conversation } from '../state/types.ts'

interface SidebarProps {
  connection: ConnectionState
  conversations: Conversation[]
  activeId: string
  onRetry: () => void
  onNewChat: () => void
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

function AgentInfo({ connection, onRetry }: Pick<SidebarProps, 'connection' | 'onRetry'>) {
  const statusText =
    connection.status === 'ready'
      ? connection.card.capabilities?.streaming
        ? 'Connected \u00b7 streaming'
        : 'Connected'
      : connection.status === 'connecting'
        ? 'Connecting\u2026'
        : connection.message

  return (
    <section className="agent-card" aria-label="Agent">
      {connection.status === 'ready' && (
        <>
          <p className="agent-card__name">{connection.card.name}</p>
          {connection.card.description && <p className="agent-card__description">{connection.card.description}</p>}
          {connection.card.skills.length > 0 && (
            <ul className="agent-card__skills" aria-label="Skills">
              {connection.card.skills.map((skill) => (
                <li key={skill.id} className="chip" title={skill.description}>
                  {skill.name}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <p className={`status status--${connection.status}`} role="status">
        <span className="status__dot" aria-hidden="true" />
        <span>{statusText}</span>
        {connection.status === 'error' && (
          <button type="button" className="link-button" onClick={onRetry}>
            Retry
          </button>
        )}
      </p>
    </section>
  )
}

export function Sidebar({ connection, conversations, activeId, onRetry, onNewChat, onSelect, onDelete }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <span className="sidebar__logo" aria-hidden="true">
          &#9993;
        </span>
        A2A Chat
      </div>
      <AgentInfo connection={connection} onRetry={onRetry} />
      <button type="button" className="sidebar__new" onClick={onNewChat}>
        + New chat
      </button>
      <h2 className="sidebar__heading">Conversations</h2>
      <ul className="conversation-list">
        {conversations.map((conversation) => (
          <li
            key={conversation.id}
            className={`conversation${conversation.id === activeId ? ' conversation--active' : ''}`}
          >
            <button
              type="button"
              className="conversation__select"
              aria-current={conversation.id === activeId ? 'true' : undefined}
              onClick={() => onSelect(conversation.id)}
            >
              {conversation.title}
            </button>
            <button
              type="button"
              className="conversation__delete"
              aria-label={`Delete conversation ${conversation.title}`}
              onClick={() => onDelete(conversation.id)}
            >
              &#10005;
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
