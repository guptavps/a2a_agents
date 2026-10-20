export type RunState =
  | 'submitted'
  | 'working'
  | 'completed'
  | 'failed'
  | 'canceled'
  | 'rejected'
  | 'input_required'
  | 'auth_required'

export type UiEvent =
  | { kind: 'state'; state: RunState }
  | { kind: 'intent'; intent: string; confidence: number; rationale: string }
  | { kind: 'reasoning'; text: string }
  | { kind: 'commentary'; text: string }
  | { kind: 'answer'; text: string; append: boolean }
  | { kind: 'error'; text: string }

export const TERMINAL_STATES: ReadonlySet<RunState> = new Set([
  'completed',
  'failed',
  'canceled',
  'rejected',
])
