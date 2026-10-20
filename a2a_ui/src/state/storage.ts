import type { AgentMessage, ChatMessage, Conversation, StepItem } from './types.ts'

export interface KeyValueStore {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
}

const STORAGE_KEY = 'a2a_ui.conversations'
const STORAGE_VERSION = 1
export const MAX_CONVERSATIONS = 50

const TURN_STATUSES = new Set(['running', 'done', 'error', 'canceled'])
const isObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null

function isStep(value: unknown): value is StepItem {
  if (!isObject(value)) return false
  if (value.kind === 'intent') {
    return typeof value.intent === 'string' && typeof value.confidence === 'number' && typeof value.rationale === 'string'
  }
  return (value.kind === 'reasoning' || value.kind === 'commentary') && typeof value.text === 'string'
}

function isMessage(value: unknown): value is ChatMessage {
  if (!isObject(value) || typeof value.id !== 'string') return false
  if (value.role === 'user') return typeof value.text === 'string'
  return (
    value.role === 'agent' &&
    typeof value.status === 'string' &&
    TURN_STATUSES.has(value.status) &&
    typeof value.answer === 'string' &&
    Array.isArray(value.steps) &&
    value.steps.every(isStep) &&
    (value.error === undefined || typeof value.error === 'string')
  )
}

function isConversation(value: unknown): value is Conversation {
  return (
    isObject(value) &&
    typeof value.id === 'string' &&
    typeof value.title === 'string' &&
    typeof value.updatedAt === 'number' &&
    Array.isArray(value.messages) &&
    value.messages.every(isMessage)
  )
}

// A turn still marked running was interrupted by a reload; nothing is streaming into it any more.
function settleInterrupted(conversation: Conversation): Conversation {
  const messages = conversation.messages.map((message): ChatMessage =>
    message.role === 'agent' && message.status === 'running'
      ? ({ ...message, status: 'canceled' } satisfies AgentMessage)
      : message,
  )
  return { ...conversation, messages }
}

export function loadConversations(store: KeyValueStore): Conversation[] {
  try {
    const raw = store.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    if (!isObject(parsed) || parsed.version !== STORAGE_VERSION || !Array.isArray(parsed.conversations)) return []
    return parsed.conversations.filter(isConversation).slice(0, MAX_CONVERSATIONS).map(settleInterrupted)
  } catch {
    return []
  }
}

export function saveConversations(store: KeyValueStore, conversations: Conversation[]): void {
  try {
    const payload = { version: STORAGE_VERSION, conversations: conversations.slice(0, MAX_CONVERSATIONS) }
    store.setItem(STORAGE_KEY, JSON.stringify(payload))
  } catch (error) {
    console.warn('Could not persist conversations', error)
  }
}
