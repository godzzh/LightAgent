import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import type { ApiEnvelope } from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

export const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

export function getToken(): string {
  return localStorage.getItem('la_token') || ''
}

export function setToken(token: string) {
  if (token) localStorage.setItem('la_token', token)
  else localStorage.removeItem('la_token')
}

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** 统一错误提示注册点：由 App.vue 注入 message 实例 */
type Notifier = (msg: string) => void
let notify: Notifier = (msg) => console.error(msg)
export function setNotifier(fn: Notifier) {
  notify = fn
}

let redirecting = false

http.interceptors.response.use(
  (response) => {
    const payload = response.data as ApiEnvelope<unknown>
    if (payload && typeof payload === 'object' && 'code' in payload) {
      if (payload.code === 0) return payload.data as any
      notify(payload.message || '请求失败')
      return Promise.reject(new Error(payload.message || '请求失败'))
    }
    return response.data
  },
  (error) => {
    const status = error?.response?.status
    const message =
      error?.response?.data?.message ||
      error?.response?.data?.detail ||
      (error.code === 'ECONNABORTED' ? '请求超时，请稍后重试' : '网络异常，请检查后端服务')
    if (status === 401) {
      setToken('')
      if (!redirecting && !location.pathname.startsWith('/login')) {
        redirecting = true
        location.href = '/login'
      }
    } else {
      notify(typeof message === 'string' ? message : '请求失败')
    }
    return Promise.reject(new Error(typeof message === 'string' ? message : '请求失败'))
  },
)

export function request<T>(config: AxiosRequestConfig): Promise<T> {
  return http.request<any, T>(config) as unknown as Promise<T>
}

export const api = {
  get: <T>(url: string, params?: Record<string, any>) => request<T>({ url, method: 'get', params }),
  post: <T>(url: string, data?: any) => request<T>({ url, method: 'post', data }),
  patch: <T>(url: string, data?: any) => request<T>({ url, method: 'patch', data }),
  put: <T>(url: string, data?: any) => request<T>({ url, method: 'put', data }),
  del: <T>(url: string, params?: Record<string, any>) => request<T>({ url, method: 'delete', params }),
}

/**
 * POST + SSE 流读取（EventSource 不支持 POST，这里用 fetch + ReadableStream）。
 * 返回一个可取消的句柄：{ abort() }
 */
export function streamPost(
  url: string,
  body: Record<string, any>,
  onEvent: (event: string, data: Record<string, any>) => void,
  options: { onError?: (e: Error) => void; onClose?: () => void } = {},
): { abort: () => void } {
  const controller = new AbortController()
  const target = `${BASE_URL}${url}`

  ;(async () => {
    try {
      const resp = await fetch(target, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!resp.ok) {
        let detail = `请求失败(${resp.status})`
        try {
          const err = await resp.json()
          detail = err?.message || detail
        } catch {
          /* ignore */
        }
        throw new Error(detail)
      }
      if (!resp.body) throw new Error('当前浏览器不支持流式响应')

      const reader = resp.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      // 逐块解析 SSE: event: xxx\ndata: {...}\n\n
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''
        for (const block of blocks) {
          const lines = block.split('\n')
          let eventName = 'message'
          const dataLines: string[] = []
          for (const line of lines) {
            if (line.startsWith('event:')) eventName = line.slice(6).trim()
            else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
          }
          if (!dataLines.length) continue
          try {
            onEvent(eventName, JSON.parse(dataLines.join('\n')))
          } catch {
            /* 忽略非法片段 */
          }
        }
      }
      options.onClose?.()
    } catch (e: any) {
      if (e?.name === 'AbortError') {
        options.onClose?.()
        return
      }
      options.onError?.(e instanceof Error ? e : new Error(String(e)))
    }
  })()

  return { abort: () => controller.abort() }
}
