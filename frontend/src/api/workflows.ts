import { api, streamPost } from './client'
import type { NodeDefinition, Paged, SSEEvent, Workflow } from '@/types'

export const workflowApi = {
  list: (params: Record<string, any> = {}) => api.get<Paged<Workflow>>('/workflows', params),
  detail: (id: string) => api.get<Workflow>(`/workflows/${id}`),
  create: (data: Record<string, any>) => api.post<Workflow>('/workflows', data),
  update: (id: string, data: Record<string, any>) => api.patch<Workflow>(`/workflows/${id}`, data),
  remove: (id: string) => api.del(`/workflows/${id}`),
  validate: (id: string) => api.post<{ ok: boolean; errors: string[] }>(`/workflows/${id}/validate`),
  nodeDefinitions: () => api.get<NodeDefinition[]>('/workflows/node-definitions'),
  runs: (id: string, params: Record<string, any> = {}) =>
    api.get<Paged<any>>(`/workflows/${id}/runs`, params),
  runDetail: (runId: string) => api.get<any>(`/workflows/runs/${runId}`),
  run: (id: string, inputs: Record<string, any>) =>
    api.post<any>(`/workflows/${id}/run`, { inputs, stream: false }),
  runStream: (
    id: string,
    inputs: Record<string, any>,
    handlers: { onEvent: (ev: SSEEvent) => void; onError?: (e: Error) => void; onClose?: () => void },
  ) =>
    streamPost(
      `/workflows/${id}/run`,
      { inputs, stream: true },
      (event, data) => handlers.onEvent({ event, data }),
      handlers,
    ),
}
