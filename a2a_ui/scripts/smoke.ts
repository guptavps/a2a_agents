// Prints the raw event stream so the event mapper can be built against real data.
import { TaskState } from '@a2a-js/sdk'
import type { Message, Part } from '@a2a-js/sdk'
import { connectToAgent, streamMessage } from '../src/a2a/client.ts'

const agentUrl = process.env.VITE_AGENT_URL ?? 'http://localhost:8092'
const prompt = process.argv[2] ?? 'Please close loan 12345'

function describeParts(parts: Part[]): string {
  return parts
    .map((part) => {
      const kind = part.content?.$case ?? 'empty'
      const value = part.content?.$case === 'text' ? part.content.value.slice(0, 160) : ''
      return `[${kind}${part.metadata ? ` meta=${JSON.stringify(part.metadata)}` : ''}] ${value}`
    })
    .join(' | ')
}

function describeMessage(message?: Message): string {
  return message ? describeParts(message.parts) : '(no message)'
}

const connection = await connectToAgent(agentUrl)
console.log(`card: ${connection.card.name}, protocol ${connection.client.protocolVersion}, streaming=${connection.card.capabilities?.streaming}`)

const contextId = crypto.randomUUID()
let index = 0
for await (const event of streamMessage(connection, prompt, contextId)) {
  const payload = event.payload
  index += 1
  switch (payload?.$case) {
    case 'task':
      console.log(`#${index} task state=${TaskState[payload.value.status?.state ?? 0]} artifacts=${payload.value.artifacts.length}`)
      break
    case 'message':
      console.log(`#${index} message: ${describeMessage(payload.value)}`)
      break
    case 'statusUpdate':
      console.log(`#${index} status=${TaskState[payload.value.status?.state ?? 0]} :: ${describeMessage(payload.value.status?.message)}`)
      break
    case 'artifactUpdate':
      console.log(`#${index} artifact append=${payload.value.append} last=${payload.value.lastChunk} :: ${describeParts(payload.value.artifact?.parts ?? [])}`)
      break
    default:
      console.log(`#${index} (empty payload)`)
  }
}
console.log(`done: ${index} events`)
