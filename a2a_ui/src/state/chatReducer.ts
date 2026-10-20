import type { UiEvent } from '../a2a/types.ts'
import { DEFAULT_TITLE } from './types.ts'
import type { AgentMessage, ChatMessage, ChatState, Conversation, StepItem } from './types.ts'

export type ChatAction =
  | { type: 'conversationCreated'; id: string; now: number }
  | { type: 'conversationSelected'; id: string }
  | { type: 'conversationDeleted'; id: string; replacementId: string; now: number }
  | {
      type: 'turnStarted'
      conversationId: string
      userMessageId: string
      agentMessageId: string
      text: string
      now: number
    }
  | { type: 'agentEvent'; conversationId: string; event: UiEvent }
  | { type: 'turnEnded'; conversationId: string; outcome: 'finished' | 'aborted' | 'failed'; error?: string }

const TITLE_MAX_LENGTH = 40
const GENERIC_FAILURE = 'The request failed. Please try again.'
const AUTH_UNSUPPORTED = 'The agent requires authentication, which this app does not support yet.'

export function newConversation(id: string, now: number): Conversation {
  return { id, title: DEFAULT_TITLE, messages: [], updatedAt: now }
}

export function createInitialState(stored: Conversation[], freshId: string, now: number): ChatState {
  const conversations = stored.length > 0 ? stored : [newConversation(freshId, now)]
  return { conversations, activeId: conversations[0].id }
}

export function lastAgentTurn(conversation: Conversation | undefined): AgentMessage | undefined {
  const last = conversation?.messages.at(-1)
  return last?.role === 'agent' ? last : undefined
}

export function isRunning(conversation: Conversation | undefined): boolean {
  return lastAgentTurn(conversation)?.status === 'running'
}

function titleFrom(text: string): string {
  const flat = text.replace(/\s+/g, ' ').trim()
  return flat.length > TITLE_MAX_LENGTH ? `${flat.slice(0, TITLE_MAX_LENGTH - 1)}\u2026` : flat
}

function addStep(turn: AgentMessage, step: StepItem): AgentMessage {
  const previous = turn.steps.at(-1)
  if (previous && JSON.stringify(previous) === JSON.stringify(step)) return turn
  if (step.kind !== 'intent' && step.text.trim() === turn.answer.trim()) return turn
  return { ...turn, steps: [...turn.steps, step] }
}

function setAnswer(turn: AgentMessage, text: string, append: boolean): AgentMessage {
  const answer = append ? turn.answer + text : text
  // The server repeats its final text as commentary first; show it only once, as the answer.
  const steps = turn.steps.filter(
    (step) => step.kind === 'intent' || step.kind === 'reasoning' || step.text.trim() !== answer.trim(),
  )
  return { ...turn, answer, steps }
}

function applyEvent(turn: AgentMessage, event: UiEvent): AgentMessage {
  switch (event.kind) {
    case 'intent':
      return addStep(turn, event)
    case 'reasoning':
    case 'commentary':
      return addStep(turn, { kind: event.kind, text: event.text })
    case 'answer':
      return setAnswer(turn, event.text, event.append)
    case 'error':
      return { ...turn, status: 'error', error: event.text }
    case 'state':
      switch (event.state) {
        case 'completed':
        case 'input_required':
          return { ...turn, status: 'done' }
        case 'canceled':
          return { ...turn, status: 'canceled' }
        case 'failed':
        case 'rejected':
          return turn.status === 'error' ? turn : { ...turn, status: 'error', error: GENERIC_FAILURE }
        case 'auth_required':
          return { ...turn, status: 'error', error: AUTH_UNSUPPORTED }
        default:
          return turn
      }
  }
}

function updateTurn(
  state: ChatState,
  conversationId: string,
  update: (turn: AgentMessage) => AgentMessage,
): ChatState {
  return {
    ...state,
    conversations: state.conversations.map((conversation) => {
      const turn = lastAgentTurn(conversation)
      if (conversation.id !== conversationId || !turn || turn.status !== 'running') return conversation
      const messages: ChatMessage[] = [...conversation.messages.slice(0, -1), update(turn)]
      return { ...conversation, messages }
    }),
  }
}

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'conversationCreated':
      return {
        conversations: [newConversation(action.id, action.now), ...state.conversations],
        activeId: action.id,
      }
    case 'conversationSelected':
      return state.conversations.some((c) => c.id === action.id) ? { ...state, activeId: action.id } : state
    case 'conversationDeleted': {
      const remaining = state.conversations.filter((c) => c.id !== action.id)
      if (remaining.length === state.conversations.length) return state
      const conversations = remaining.length > 0 ? remaining : [newConversation(action.replacementId, action.now)]
      const activeId = conversations.some((c) => c.id === state.activeId) ? state.activeId : conversations[0].id
      return { conversations, activeId }
    }
    case 'turnStarted': {
      const target = state.conversations.find((c) => c.id === action.conversationId)
      if (!target || isRunning(target)) return state
      return {
        ...state,
        conversations: state.conversations.map((conversation) => {
          if (conversation.id !== action.conversationId) return conversation
          return {
            ...conversation,
            title: conversation.title === DEFAULT_TITLE ? titleFrom(action.text) : conversation.title,
            updatedAt: action.now,
            messages: [
              ...conversation.messages,
              { id: action.userMessageId, role: 'user', text: action.text },
              { id: action.agentMessageId, role: 'agent', status: 'running', steps: [], answer: '' },
            ],
          }
        }),
      }
    }
    case 'agentEvent':
      return updateTurn(state, action.conversationId, (turn) => applyEvent(turn, action.event))
    case 'turnEnded':
      return updateTurn(state, action.conversationId, (turn) => {
        switch (action.outcome) {
          case 'finished':
            return { ...turn, status: 'done' }
          case 'aborted':
            return { ...turn, status: 'canceled' }
          case 'failed':
            return { ...turn, status: 'error', error: action.error ?? GENERIC_FAILURE }
        }
      })
  }
}
