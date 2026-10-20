import { Role, TaskState } from '@a2a-js/sdk'
import type { Message, Part, StreamResponse } from '@a2a-js/sdk'
import type { RunState, UiEvent } from './types.ts'

const RUN_STATES: Partial<Record<TaskState, RunState>> = {
  [TaskState.TASK_STATE_SUBMITTED]: 'submitted',
  [TaskState.TASK_STATE_WORKING]: 'working',
  [TaskState.TASK_STATE_COMPLETED]: 'completed',
  [TaskState.TASK_STATE_FAILED]: 'failed',
  [TaskState.TASK_STATE_CANCELED]: 'canceled',
  [TaskState.TASK_STATE_REJECTED]: 'rejected',
  [TaskState.TASK_STATE_INPUT_REQUIRED]: 'input_required',
  [TaskState.TASK_STATE_AUTH_REQUIRED]: 'auth_required',
}

const GENERIC_FAILURE = 'The agent could not complete the request.'

type TextKind = 'commentary' | 'answer' | 'error'

function parseIntent(text: string): UiEvent | undefined {
  if (!text.startsWith('{')) return undefined
  try {
    const value: unknown = JSON.parse(text)
    if (typeof value !== 'object' || value === null) return undefined
    const { intent, confidence, rationale } = value as Record<string, unknown>
    if (typeof intent !== 'string' || typeof confidence !== 'number' || typeof rationale !== 'string') {
      return undefined
    }
    return { kind: 'intent', intent, confidence, rationale }
  } catch {
    return undefined
  }
}

function mapParts(parts: Part[], kind: TextKind, append = false): UiEvent[] {
  const events: UiEvent[] = []
  for (const part of parts) {
    if (part.content?.$case !== 'text') continue
    const text = part.content.value
    if (!text.trim()) continue
    if (part.metadata?.adk_thought === true) {
      events.push({ kind: 'reasoning', text })
      continue
    }
    const intent = kind === 'error' ? undefined : parseIntent(text.trim())
    if (intent) {
      events.push(intent)
    } else if (kind === 'answer') {
      events.push({ kind: 'answer', text, append })
    } else {
      events.push({ kind, text })
    }
  }
  return events
}

function kindForState(state: RunState): TextKind {
  switch (state) {
    case 'completed':
    case 'input_required':
      return 'answer'
    case 'failed':
    case 'rejected':
      return 'error'
    default:
      return 'commentary'
  }
}

function mapStatus(state: TaskState | undefined, message: Message | undefined): UiEvent[] {
  const runState = state === undefined ? undefined : RUN_STATES[state]
  if (!runState) return []
  const events: UiEvent[] = [{ kind: 'state', state: runState }]
  const kind = kindForState(runState)
  const textEvents = message ? mapParts(message.parts, kind) : []
  if (kind === 'error' && textEvents.length === 0) {
    events.push({ kind: 'error', text: GENERIC_FAILURE })
  }
  return [...events, ...textEvents]
}

export function mapStreamResponse(response: StreamResponse): UiEvent[] {
  const payload = response.payload
  switch (payload?.$case) {
    case 'task': {
      const task = payload.value
      return [
        ...mapStatus(task.status?.state, task.status?.message),
        ...task.artifacts.flatMap((artifact) => mapParts(artifact.parts, 'answer')),
      ]
    }
    case 'message':
      return payload.value.role === Role.ROLE_AGENT ? mapParts(payload.value.parts, 'answer') : []
    case 'statusUpdate':
      return mapStatus(payload.value.status?.state, payload.value.status?.message)
    case 'artifactUpdate':
      return mapParts(payload.value.artifact?.parts ?? [], 'answer', payload.value.append)
    default:
      return []
  }
}
