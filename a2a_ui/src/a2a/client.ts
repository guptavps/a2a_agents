import { Role } from '@a2a-js/sdk'
import type { AgentCard, SendMessageRequest, StreamResponse } from '@a2a-js/sdk'
import { Client, ClientFactory, DefaultAgentCardResolver } from '@a2a-js/sdk/client'

export interface AgentConnection {
  card: AgentCard
  client: Client
}

// The card advertises the server's own bind address; pin every interface to the URL we were configured with.
function pinInterfaceUrls(card: AgentCard, agentUrl: string): AgentCard {
  const url = agentUrl.replace(/\/+$/, '') + '/'
  return {
    ...card,
    supportedInterfaces: card.supportedInterfaces.map((entry) => ({ ...entry, url })),
  }
}

export async function connectToAgent(agentUrl: string): Promise<AgentConnection> {
  const card = pinInterfaceUrls(await new DefaultAgentCardResolver().resolve(agentUrl), agentUrl)
  const client = await new ClientFactory().createFromAgentCard(card)
  return { card, client }
}

export function streamMessage(
  { client }: AgentConnection,
  text: string,
  contextId: string,
  signal?: AbortSignal,
): AsyncGenerator<StreamResponse, void, undefined> {
  const request: SendMessageRequest = {
    tenant: '',
    message: {
      messageId: crypto.randomUUID(),
      contextId,
      taskId: '',
      role: Role.ROLE_USER,
      parts: [
        { content: { $case: 'text', value: text }, metadata: undefined, filename: '', mediaType: 'text/plain' },
      ],
      metadata: undefined,
      extensions: [],
      referenceTaskIds: [],
    },
    configuration: undefined,
    metadata: undefined,
  }
  return client.sendMessageStream(request, { signal })
}
