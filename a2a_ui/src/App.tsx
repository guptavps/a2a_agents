import { ChatPanel } from './components/ChatPanel.tsx'
import { Sidebar } from './components/Sidebar.tsx'
import { AGENT_URL } from './config.ts'
import { useAgentConnection } from './hooks/useAgentConnection.ts'
import { useChat } from './hooks/useChat.ts'
import { useChatRunner } from './hooks/useChatRunner.ts'

export default function App() {
  const { state, dispatch } = useChat()
  const { state: connection, retry } = useAgentConnection(AGENT_URL)
  const { send, stop } = useChatRunner(connection, dispatch)
  const active = state.conversations.find((conversation) => conversation.id === state.activeId) ?? state.conversations[0]

  return (
    <div className="app">
      <Sidebar
        connection={connection}
        conversations={state.conversations}
        activeId={active.id}
        onRetry={retry}
        onNewChat={() => dispatch({ type: 'conversationCreated', id: crypto.randomUUID(), now: Date.now() })}
        onSelect={(id) => dispatch({ type: 'conversationSelected', id })}
        onDelete={(id) => {
          stop(id)
          dispatch({ type: 'conversationDeleted', id, replacementId: crypto.randomUUID(), now: Date.now() })
        }}
      />
      <ChatPanel
        conversation={active}
        connection={connection}
        onRetry={retry}
        onSend={(text) => void send(active.id, text)}
        onStop={() => stop(active.id)}
      />
    </div>
  )
}
