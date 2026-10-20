import { useCallback, useEffect, useRef } from 'react'
import type { Dispatch } from 'react'
import { streamMessage } from '../a2a/client.ts'
import { mapStreamResponse } from '../a2a/eventMapper.ts'
import type { ChatAction } from '../state/chatReducer.ts'
import type { ConnectionState } from './useAgentConnection.ts'

const IDLE_TIMEOUT_MS = 120_000
const REQUEST_FAILED = 'Could not complete the request. Check that the agent is running and try again.'
const TIMED_OUT = 'The agent stopped responding. Please try again.'

export function useChatRunner(connection: ConnectionState, dispatch: Dispatch<ChatAction>) {
  const controllers = useRef(new Map<string, AbortController>())

  useEffect(() => {
    const active = controllers.current
    return () => active.forEach((controller) => controller.abort())
  }, [])

  const send = useCallback(
    async (conversationId: string, text: string) => {
      if (connection.status !== 'ready' || controllers.current.has(conversationId)) return

      const controller = new AbortController()
      controllers.current.set(conversationId, controller)
      let timedOut = false
      let timer = 0
      // The limit applies to silence between events so long streaming answers are never cut off.
      const armIdleTimer = () => {
        window.clearTimeout(timer)
        timer = window.setTimeout(() => {
          timedOut = true
          controller.abort()
        }, IDLE_TIMEOUT_MS)
      }

      dispatch({
        type: 'turnStarted',
        conversationId,
        userMessageId: crypto.randomUUID(),
        agentMessageId: crypto.randomUUID(),
        text,
        now: Date.now(),
      })
      armIdleTimer()
      try {
        for await (const response of streamMessage(connection.connection, text, conversationId, controller.signal)) {
          armIdleTimer()
          for (const event of mapStreamResponse(response)) {
            dispatch({ type: 'agentEvent', conversationId, event })
          }
        }
        dispatch({ type: 'turnEnded', conversationId, outcome: 'finished' })
      } catch (error) {
        if (controller.signal.aborted) {
          dispatch(
            timedOut
              ? { type: 'turnEnded', conversationId, outcome: 'failed', error: TIMED_OUT }
              : { type: 'turnEnded', conversationId, outcome: 'aborted' },
          )
        } else {
          console.error('Agent request failed', error)
          dispatch({ type: 'turnEnded', conversationId, outcome: 'failed', error: REQUEST_FAILED })
        }
      } finally {
        window.clearTimeout(timer)
        controllers.current.delete(conversationId)
      }
    },
    [connection, dispatch],
  )

  const stop = useCallback((conversationId: string) => {
    controllers.current.get(conversationId)?.abort()
  }, [])

  return { send, stop }
}
