import { api } from './client'
import type { Paged, Application, LoginResult, User, Workspace } from '@/types'

export const authApi = {
  login: (account: string, password: string) =>
    api.post<LoginResult>('/auth/login', { account, password }),
  register: (data: { username: string; email: string; password: string }) =>
    api.post<LoginResult>('/auth/register', data),
  me: () => api.get<{ user: User; workspace: Workspace }>('/auth/me'),
  update: (data: { username?: string; password?: string }) => api.patch<User>('/auth/me', data),
}

export const appApi = {
  list: (params: Record<string, any>) => api.get<Paged<Application>>('/applications', params),
  templates: () => api.get<any[]>('/applications/templates'),
  detail: (id: string) => api.get<Application>(`/applications/${id}`),
  create: (data: Record<string, any>) => api.post<Application>('/applications', data),
  update: (id: string, data: Record<string, any>) => api.patch<Application>(`/applications/${id}`, data),
  remove: (id: string) => api.del(`/applications/${id}`),
  copy: (id: string) => api.post<Application>(`/applications/${id}/copy`),
  publish: (id: string, data: Record<string, any>) =>
    api.post<any>(`/applications/${id}/publish`, data),
  unpublish: (id: string) => api.post<Application>(`/applications/${id}/unpublish`),
  versions: (id: string) => api.get<any[]>(`/applications/${id}/versions`),
  keys: (id: string) => api.get<any[]>(`/applications/${id}/keys`),
  createKey: (id: string, name = 'default') =>
    api.post<any>(`/applications/${id}/keys?name=${encodeURIComponent(name)}`),
  deleteKey: (id: string, keyId: string) => api.del(`/applications/${id}/keys/${keyId}`),
  stats: (id: string) => api.get<{ runs: number; tokens: number }>(`/applications/${id}/stats`),
}

export const dashboardApi = {
  overview: () => api.get<any>('/dashboard/overview'),
  recent: () => api.get<any>('/dashboard/recent'),
  trend: () => api.get<any>('/dashboard/trend'),
}

export const logApi = {
  runs: (params: Record<string, any>) => api.get<Paged<any>>('/logs/runs', params),
  stats: (days = 7) => api.get<any>('/logs/stats', { days }),
}
