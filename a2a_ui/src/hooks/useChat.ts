import { useEffect, useReducer } from 'react'
import { chatReducer, createInitialState } from '../state/chatReducer.ts'
import { loadConversations, saveConversations } from '../state/storage.ts'

const SAVE_DELAY_MS = 300

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, undefined, () =>
    createInitialState(loadConversations(window.localStorage), crypto.randomUUID(), Date.now()),
  )

  // Streaming dispatches many events per second; debounce so storage is written once things settle.
  useEffect(() => {
    const timer = window.setTimeout(() => saveConversations(window.localStorage, state.conversations), SAVE_DELAY_MS)
    return () => window.clearTimeout(timer)
  }, [state.conversations])

  return { state, dispatch }
}
