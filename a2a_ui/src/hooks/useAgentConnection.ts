import { useCallback, useEffect, useState } from 'react'
import type { AgentCard } from '@a2a-js/sdk'
import { connectToAgent } from '../a2a/client.ts'
import type { AgentConnection } from '../a2a/client.ts'

export type ConnectionState =
  | { status: 'connecting' }
  | { status: 'ready'; connection: AgentConnection; card: AgentCard }
  | { status: 'error'; message: string }

export function useAgentConnection(agentUrl: string): { state: ConnectionState; retry: () => void } {
  const [state, setState] = useState<ConnectionState>({ status: 'connecting' })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    connectToAgent(agentUrl).then(
      (connection) => {
        if (!cancelled) setState({ status: 'ready', connection, card: connection.card })
      },
      (error: unknown) => {
        console.error('Agent connection failed', error)
        if (!cancelled) setState({ status: 'error', message: `Could not reach the agent at ${agentUrl}.` })
      },
    )
    return () => {
      cancelled = true
    }
  }, [agentUrl, attempt])

  const retry = useCallback(() => {
    setState({ status: 'connecting' })
    setAttempt((value) => value + 1)
  }, [])
  return { state, retry }
}
