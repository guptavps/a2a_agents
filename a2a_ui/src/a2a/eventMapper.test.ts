import assert from 'node:assert/strict'
import { test } from 'node:test'
import { Role, TaskState } from '@a2a-js/sdk'
import type { Artifact, Message, Part, StreamResponse } from '@a2a-js/sdk'
import { mapStreamResponse } from './eventMapper.ts'

const part = (text: string, metadata?: Record<string, unknown>): Part => ({
  content: { $case: 'text', value: text },
  metadata,
  filename: '',
  mediaType: 'text/plain',
})

const message = (role: Role, ...parts: Part[]): Message => ({
  messageId: 'm1',
  contextId: 'c1',
  taskId: 't1',
  role,
  parts,
  metadata: undefined,
  extensions: [],
  referenceTaskIds: [],
})

const artifact = (...parts: Part[]): Artifact => ({
  artifactId: 'a1',
  name: '',
  description: '',
  parts,
  metadata: undefined,
  extensions: [],
})

const status = (state: TaskState, ...parts: Part[]): StreamResponse => ({
  payload: {
    $case: 'statusUpdate',
    value: {
      taskId: 't1',
      contextId: 'c1',
      status: {
        state,
        message: parts.length ? message(Role.ROLE_AGENT, ...parts) : undefined,
        timestamp: undefined,
      },
      metadata: undefined,
    },
  },
})

const artifactUpdate = (append: boolean, ...parts: Part[]): StreamResponse => ({
  payload: {
    $case: 'artifactUpdate',
    value: { taskId: 't1', contextId: 'c1', artifact: artifact(...parts), append, lastChunk: true, metadata: undefined },
  },
})

const INTENT_JSON = '{"intent":"loan_closure","confidence":1.0,"rationale":"The user explicitly requests to close loan 12345."}'

test('submitted task maps to a state event', () => {
  const response: StreamResponse = {
    payload: {
      $case: 'task',
      value: {
        id: 't1',
        contextId: 'c1',
        status: { state: TaskState.TASK_STATE_SUBMITTED, message: undefined, timestamp: undefined },
        artifacts: [],
        history: [],
        metadata: undefined,
      },
    },
  }
  assert.deepEqual(mapStreamResponse(response), [{ kind: 'state', state: 'submitted' }])
})

test('empty working update yields only a state event', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_WORKING)), [{ kind: 'state', state: 'working' }])
})

test('intent JSON in a working update becomes an intent event, not raw text', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_WORKING, part(INTENT_JSON))), [
    { kind: 'state', state: 'working' },
    { kind: 'intent', intent: 'loan_closure', confidence: 1, rationale: 'The user explicitly requests to close loan 12345.' },
  ])
})

test('plain working text is commentary', () => {
  assert.deepEqual(
    mapStreamResponse(status(TaskState.TASK_STATE_WORKING, part('The loan closure for application ID 12345 has succeeded.'))),
    [
      { kind: 'state', state: 'working' },
      { kind: 'commentary', text: 'The loan closure for application ID 12345 has succeeded.' },
    ],
  )
})

test('artifact text is the final answer', () => {
  assert.deepEqual(mapStreamResponse(artifactUpdate(false, part('Done.'))), [
    { kind: 'answer', text: 'Done.', append: false },
  ])
})

test('appended artifact chunks keep the append flag', () => {
  assert.deepEqual(mapStreamResponse(artifactUpdate(true, part('more'))), [
    { kind: 'answer', text: 'more', append: true },
  ])
})

test('an artifact containing only intent JSON is not shown as an answer', () => {
  assert.deepEqual(mapStreamResponse(artifactUpdate(false, part(INTENT_JSON))), [
    { kind: 'intent', intent: 'loan_closure', confidence: 1, rationale: 'The user explicitly requests to close loan 12345.' },
  ])
})

test('ADK thought parts are reasoning', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_WORKING, part('Checking the loan id', { adk_thought: true }))), [
    { kind: 'state', state: 'working' },
    { kind: 'reasoning', text: 'Checking the loan id' },
  ])
})

test('failed status surfaces the server message as an error', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_FAILED, part('No API key was provided.'))), [
    { kind: 'state', state: 'failed' },
    { kind: 'error', text: 'No API key was provided.' },
  ])
})

test('failed status without a message uses a generic error', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_FAILED)), [
    { kind: 'state', state: 'failed' },
    { kind: 'error', text: 'The agent could not complete the request.' },
  ])
})

test('input_required message is shown as an answer so the user can reply', () => {
  assert.deepEqual(mapStreamResponse(status(TaskState.TASK_STATE_INPUT_REQUIRED, part('Which loan?'))), [
    { kind: 'state', state: 'input_required' },
    { kind: 'answer', text: 'Which loan?', append: false },
  ])
})

test('user-role messages and empty payloads are ignored', () => {
  assert.deepEqual(
    mapStreamResponse({ payload: { $case: 'message', value: message(Role.ROLE_USER, part('hi')) } }),
    [],
  )
  assert.deepEqual(mapStreamResponse({ payload: undefined }), [])
})
