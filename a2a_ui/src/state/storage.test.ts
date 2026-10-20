import assert from 'node:assert/strict'
import { test } from 'node:test'
import { MAX_CONVERSATIONS, loadConversations, saveConversations } from './storage.ts'
import type { KeyValueStore } from './storage.ts'
import type { Conversation } from './types.ts'

function memoryStore(initial?: string): KeyValueStore & { raw: () => string | null } {
  let value: string | null = initial ?? null
  return {
    getItem: () => value,
    setItem: (_key, next) => {
      value = next
    },
    raw: () => value,
  }
}

const conversation = (id: string, status: 'running' | 'done' = 'done'): Conversation => ({
  id,
  title: `Chat ${id}`,
  updatedAt: 1,
  messages: [
    { id: 'u', role: 'user', text: 'hello' },
    {
      id: 'a',
      role: 'agent',
      status,
      answer: 'hi',
      steps: [{ kind: 'intent', intent: 'loan_closure', confidence: 1, rationale: 'because' }],
    },
  ],
})

test('saved conversations round-trip', () => {
  const store = memoryStore()
  saveConversations(store, [conversation('c1')])
  assert.deepEqual(loadConversations(store), [conversation('c1')])
})

test('a turn left running is settled as canceled on load', () => {
  const store = memoryStore()
  saveConversations(store, [conversation('c1', 'running')])
  const [loaded] = loadConversations(store)
  assert.equal(loaded.messages[1].role === 'agent' && loaded.messages[1].status, 'canceled')
})

test('empty, corrupt, wrong-version and malformed data load as empty or are filtered', () => {
  assert.deepEqual(loadConversations(memoryStore()), [])
  assert.deepEqual(loadConversations(memoryStore('{not json')), [])
  assert.deepEqual(loadConversations(memoryStore('{"version":99,"conversations":[]}')), [])
  const mixed = JSON.stringify({ version: 1, conversations: [conversation('ok'), { id: 1 }, null, 'x'] })
  assert.deepEqual(
    loadConversations(memoryStore(mixed)).map((c) => c.id),
    ['ok'],
  )
})

test('a conversation with an invalid message is dropped', () => {
  const bad = { ...conversation('bad'), messages: [{ id: 'a', role: 'agent', status: 'weird', answer: '', steps: [] }] }
  const store = memoryStore(JSON.stringify({ version: 1, conversations: [bad] }))
  assert.deepEqual(loadConversations(store), [])
})

test('only the newest MAX_CONVERSATIONS are stored', () => {
  const store = memoryStore()
  const many = Array.from({ length: MAX_CONVERSATIONS + 5 }, (_, i) => conversation(`c${i}`))
  saveConversations(store, many)
  assert.equal(loadConversations(store).length, MAX_CONVERSATIONS)
})

test('a failing store does not throw', () => {
  const failing: KeyValueStore = {
    getItem: () => {
      throw new Error('denied')
    },
    setItem: () => {
      throw new Error('quota')
    },
  }
  assert.deepEqual(loadConversations(failing), [])
  assert.doesNotThrow(() => saveConversations(failing, [conversation('c1')]))
})
