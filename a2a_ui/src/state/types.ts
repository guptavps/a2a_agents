export type StepItem =
  | { kind: 'intent'; intent: string; confidence: number; rationale: string }
  | { kind: 'reasoning' | 'commentary'; text: string }

export type TurnStatus = 'running' | 'done' | 'error' | 'canceled'

export interface UserMessage {
  id: string
  role: 'user'
  text: string
}

export interface AgentMessage {
  id: string
  role: 'agent'
  status: TurnStatus
  steps: StepItem[]
  answer: string
  error?: string
}

export type ChatMessage = UserMessage | AgentMessage

// The conversation id doubles as the A2A contextId so the server keeps history per conversation.
export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: number
}

export interface ChatState {
  conversations: Conversation[]
  activeId: string
}

export const DEFAULT_TITLE = 'New chat'
