import { api } from './client'
import type { Dataset, KDocument, ModelConfig, ModelProvider, Paged, RetrieveHit, Segment, Tool } from '@/types'

export const modelApi = {
  presets: () => api.get<any[]>('/models/presets'),
  providers: () => api.get<ModelProvider[]>('/models/providers'),
  createProvider: (data: Record<string, any>) => api.post<ModelProvider>('/models/providers', data),
  updateProvider: (id: string, data: Record<string, any>) =>
    api.patch<ModelProvider>(`/models/providers/${id}`, data),
  deleteProvider: (id: string) => api.del(`/models/providers/${id}`),
  configs: (modelType?: string) =>
    api.get<ModelConfig[]>('/models/configs', modelType ? { model_type: modelType } : {}),
  createConfig: (data: Record<string, any>) => api.post<ModelConfig>('/models/configs', data),
  updateConfig: (id: string, data: Record<string, any>) =>
    api.patch<ModelConfig>(`/models/configs/${id}`, data),
  deleteConfig: (id: string) => api.del(`/models/configs/${id}`),
  test: (data: Record<string, any>) =>
    api.post<{ ok: boolean; message: string; models: string[] }>('/models/test', data),
  available: () => api.get<ModelConfig[]>('/models/available'),
}

export const knowledgeApi = {
  datasets: (params: Record<string, any> = {}) => api.get<Paged<Dataset>>('/knowledge/datasets', params),
  dataset: (id: string) => api.get<Dataset>(`/knowledge/datasets/${id}`),
  createDataset: (data: Record<string, any>) => api.post<Dataset>('/knowledge/datasets', data),
  updateDataset: (id: string, data: Record<string, any>) =>
    api.patch<Dataset>(`/knowledge/datasets/${id}`, data),
  deleteDataset: (id: string) => api.del(`/knowledge/datasets/${id}`),
  documents: (datasetId: string, params: Record<string, any> = {}) =>
    api.get<Paged<KDocument>>(`/knowledge/datasets/${datasetId}/documents`, params),
  upload: (datasetId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<any>(`/knowledge/datasets/${datasetId}/documents`, form)
  },
  deleteDocument: (docId: string) => api.del(`/knowledge/documents/${docId}`),
  reindex: (docId: string) => api.post(`/knowledge/documents/${docId}/reindex`),
  segments: (docId: string, params: Record<string, any> = {}) =>
    api.get<Paged<Segment>>(`/knowledge/documents/${docId}/segments`, params),
  updateSegment: (segmentId: string, content: string) =>
    api.patch<Segment>(`/knowledge/segments/${segmentId}`, { content }),
  retrieve: (data: Record<string, any>) =>
    api.post<{ results: RetrieveHit[]; fallback: boolean; message?: string }>('/knowledge/retrieve', data),
}

export const toolApi = {
  list: (params: Record<string, any> = {}) => api.get<Paged<Tool>>('/tools', params),
  builtin: () => api.get<any[]>('/tools/builtin'),
  create: (data: Record<string, any>) => api.post<Tool>('/tools', data),
  update: (id: string, data: Record<string, any>) => api.patch<Tool>(`/tools/${id}`, data),
  remove: (id: string) => api.del(`/tools/${id}`),
  test: (id: string, args: Record<string, any>) => api.post<any>(`/tools/${id}/test`, { arguments: args }),
  testBuiltin: (toolKey: string, args: Record<string, any>) =>
    api.post<any>(`/tools/builtin/${toolKey}/test`, { arguments: args }),
}
