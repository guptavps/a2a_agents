import assert from 'node:assert/strict'
import { test } from 'node:test'
import type { UiEvent } from '../a2a/types.ts'
import { chatReducer, createInitialState, isRunning, lastAgentTurn } from './chatReducer.ts'
import type { ChatAction } from './chatReducer.ts'
import type { ChatState } from './types.ts'

const SUCCESS = 'The loan closure for application ID 12345 has succeeded.'

function start(text = 'Please close loan 12345'): ChatState {
  const initial = createInitialState([], 'c1', 1)
  return chatReducer(initial, {
    type: 'turnStarted',
    conversationId: 'c1',
    userMessageId: 'u1',
    agentMessageId: 'a1',
    text,
    now: 2,
  })
}

function replay(state: ChatState, events: UiEvent[]): ChatState {
  return events.reduce<ChatState>(
    (next, event) => chatReducer(next, { type: 'agentEvent', conversationId: 'c1', event }),
    state,
  )
}

const turnOf = (state: ChatState) => lastAgentTurn(state.conversations[0])!

test('initial state always has one active conversation', () => {
  const state = createInitialState([], 'c1', 1)
  assert.equal(state.conversations.length, 1)
  assert.equal(state.activeId, 'c1')
})

test('turnStarted adds a user message, a running agent turn and a title', () => {
  const state = start()
  const [conversation] = state.conversations
  assert.equal(conversation.title, 'Please close loan 12345')
  assert.deepEqual(
    conversation.messages.map((m) => m.role),
    ['user', 'agent'],
  )
  assert.equal(isRunning(conversation), true)
})

test('a long first message is truncated into the title', () => {
  const title = start('x'.repeat(100)).conversations[0].title
  assert.equal(title.length, 40)
  assert.ok(title.endsWith('\u2026'))
})

test('a second turn cannot start while one is running', () => {
  const state = start()
  const again = chatReducer(state, {
    type: 'turnStarted',
    conversationId: 'c1',
    userMessageId: 'u2',
    agentMessageId: 'a2',
    text: 'again',
    now: 3,
  })
  assert.equal(again, state)
})

test('real loan-closure stream: commentary is deduped against the final answer', () => {
  const state = replay(start(), [
    { kind: 'state', state: 'submitted' },
    { kind: 'state', state: 'working' },
    { kind: 'intent', intent: 'loan_closure', confidence: 1, rationale: 'The user explicitly requests to close loan 12345.' },
    { kind: 'commentary', text: SUCCESS },
    { kind: 'answer', text: SUCCESS, append: false },
    { kind: 'state', state: 'completed' },
  ])
  const turn = turnOf(state)
  assert.equal(turn.status, 'done')
  assert.equal(turn.answer, SUCCESS)
  assert.deepEqual(
    turn.steps.map((s) => s.kind),
    ['intent'],
  )
})

test('commentary arriving after the answer is also deduped', () => {
  const turn = turnOf(
    replay(start(), [
      { kind: 'answer', text: SUCCESS, append: false },
      { kind: 'commentary', text: SUCCESS },
    ]),
  )
  assert.equal(turn.steps.length, 0)
})

test('distinct commentary and reasoning are kept in order, identical repeats collapse', () => {
  const turn = turnOf(
    replay(start(), [
      { kind: 'reasoning', text: 'Checking the loan id' },
      { kind: 'reasoning', text: 'Checking the loan id' },
      { kind: 'commentary', text: 'Calling loan closure tool' },
    ]),
  )
  assert.deepEqual(turn.steps, [
    { kind: 'reasoning', text: 'Checking the loan id' },
    { kind: 'commentary', text: 'Calling loan closure tool' },
  ])
})

test('append chunks concatenate and non-append replaces', () => {
  const chunked = turnOf(
    replay(start(), [
      { kind: 'answer', text: 'Hello ', append: false },
      { kind: 'answer', text: 'world', append: true },
    ]),
  )
  assert.equal(chunked.answer, 'Hello world')
  const replaced = turnOf(
    replay(start(), [
      { kind: 'answer', text: 'old', append: false },
      { kind: 'answer', text: 'new', append: false },
    ]),
  )
  assert.equal(replaced.answer, 'new')
})

test('failed run keeps the server error message', () => {
  const turn = turnOf(
    replay(start(), [
      { kind: 'state', state: 'working' },
      { kind: 'state', state: 'failed' },
      { kind: 'error', text: 'No API key was provided.' },
    ]),
  )
  assert.equal(turn.status, 'error')
})

test('failed state alone gets a generic error message', () => {
  const turn = turnOf(replay(start(), [{ kind: 'state', state: 'failed' }]))
  assert.equal(turn.status, 'error')
  assert.ok(turn.error)
})

test('auth_required is surfaced as an unsupported error', () => {
  const turn = turnOf(replay(start(), [{ kind: 'state', state: 'auth_required' }]))
  assert.equal(turn.status, 'error')
  assert.match(turn.error ?? '', /authentication/)
})

test('events after the turn ended are ignored', () => {
  const ended = chatReducer(start(), { type: 'turnEnded', conversationId: 'c1', outcome: 'aborted' })
  assert.equal(turnOf(ended).status, 'canceled')
  const late = replay(ended, [{ kind: 'answer', text: 'late', append: false }])
  assert.equal(turnOf(late).answer, '')
})

test('turnEnded outcomes map to statuses without overwriting a finished turn', () => {
  const finished = chatReducer(start(), { type: 'turnEnded', conversationId: 'c1', outcome: 'finished' })
  assert.equal(turnOf(finished).status, 'done')
  const failed = chatReducer(start(), { type: 'turnEnded', conversationId: 'c1', outcome: 'failed', error: 'boom' })
  assert.equal(turnOf(failed).error, 'boom')
  const after = chatReducer(finished, { type: 'turnEnded', conversationId: 'c1', outcome: 'failed', error: 'boom' })
  assert.equal(turnOf(after).status, 'done')
})

test('events for another conversation do not touch this one', () => {
  const state = start()
  const next = chatReducer(state, {
    type: 'agentEvent',
    conversationId: 'other',
    event: { kind: 'answer', text: 'x', append: false },
  } satisfies ChatAction)
  assert.equal(turnOf(next).answer, '')
})

test('new, select and delete conversations keep a valid active id', () => {
  let state = chatReducer(createInitialState([], 'c1', 1), { type: 'conversationCreated', id: 'c2', now: 5 })
  assert.deepEqual(
    state.conversations.map((c) => c.id),
    ['c2', 'c1'],
  )
  assert.equal(state.activeId, 'c2')
  state = chatReducer(state, { type: 'conversationSelected', id: 'c1' })
  assert.equal(state.activeId, 'c1')
  state = chatReducer(state, { type: 'conversationSelected', id: 'missing' })
  assert.equal(state.activeId, 'c1')
  state = chatReducer(state, { type: 'conversationDeleted', id: 'c1', replacementId: 'c3', now: 6 })
  assert.equal(state.activeId, 'c2')
  state = chatReducer(state, { type: 'conversationDeleted', id: 'c2', replacementId: 'c3', now: 7 })
  assert.deepEqual(
    state.conversations.map((c) => c.id),
    ['c3'],
  )
  assert.equal(state.activeId, 'c3')
})
