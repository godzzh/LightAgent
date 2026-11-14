import { api, streamPost } from './client'
import type { AgentRunDetail, ChatMessageItem, Paged, SSEEvent } from '@/types'

export const agentApi = {
  /** 非流式对话 */
  chat: (appId: string, query: string, sessionId?: string) =>
    api.post<any>(`/agent/${appId}/chat`, { query, session_id: sessionId, stream: false }),

  /** 流式对话，返回可中止句柄 */
  chatStream: (
    appId: string,
    body: { query: string; session_id?: string },
    handlers: {
      onEvent: (ev: SSEEvent) => void
      onError?: (e: Error) => void
      onClose?: () => void
    },
  ) =>
    streamPost(
      `/agent/${appId}/chat`,
      { ...body, stream: true },
      (event, data) => handlers.onEvent({ event, data }),
      handlers,
    ),

  conversations: (appId: string, params: Record<string, any> = {}) =>
    api.get<Paged<any>>(`/agent/applications/${appId}/conversations`, params),
  messages: (conversationId: string) =>
    api.get<{ conversation: any; messages: ChatMessageItem[] }>(
      `/agent/conversations/${conversationId}/messages`,
    ),
  deleteConversation: (conversationId: string) =>
    api.del(`/agent/conversations/${conversationId}`),
  runs: (params: Record<string, any>) => api.get<Paged<any>>('/agent/runs', params),
  runDetail: (runId: string) => api.get<AgentRunDetail>(`/agent/runs/${runId}`),
}
