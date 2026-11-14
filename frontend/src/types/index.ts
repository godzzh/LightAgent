/** 全局类型定义 */

export interface ApiEnvelope<T> {
  code: number
  message: string
  data: T
  request_id?: string
}

export interface Paged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface User {
  id: string
  username: string
  email: string
  is_superuser?: boolean
}

export interface Workspace {
  id: string
  name: string
  description?: string
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: User
  workspace: Workspace
}

export type AppType = 'chat_agent' | 'workflow' | 'chatbot'

export interface AgentToolRef {
  tool_key: string
  enabled: boolean
}

export interface AgentVariable {
  name: string
  type?: string
  default?: unknown
  description?: string
}

export interface AgentConfig {
  system_prompt: string
  user_prompt: string
  welcome_message: string
  opening_questions: string[]
  mode: 'function_calling' | 'react'
  model_config_id?: string | null
  temperature: number
  top_p: number
  max_tokens: number
  max_steps: number
  max_tool_calls: number
  max_context_messages: number
  enable_memory: boolean
  enable_tools: boolean
  enable_knowledge: boolean
  tools: AgentToolRef[]
  dataset_ids: string[]
  knowledge_top_k: number
  knowledge_threshold: number
  variables: AgentVariable[]
}

export interface Application {
  id: string
  workspace_id: string
  name: string
  description: string
  icon: string
  app_type: AppType
  status: 'draft' | 'published'
  config: Partial<AgentConfig>
  model_config_id?: string | null
  workflow_id?: string | null
  api_enabled: boolean
  run_count: number
  published_at?: string | null
  created_at: string
  updated_at: string
}

export interface ModelProvider {
  id: string
  name: string
  provider_type: string
  base_url: string
  api_key_masked: string
  has_api_key: boolean
  enabled: boolean
  is_default: boolean
  remark?: string
  configs?: ModelConfig[]
}

export interface ModelConfig {
  id: string
  provider_id: string
  display_name: string
  model_name: string
  model_type: 'llm' | 'embedding' | 'rerank'
  temperature: number
  top_p: number
  max_tokens: number
  context_window: number
  supports_streaming: boolean
  supports_tool_call: boolean
  is_default: boolean
  enabled: boolean
  provider_name?: string
}

export interface Dataset {
  id: string
  name: string
  description: string
  embedding_model_id?: string | null
  chunk_size: number
  chunk_overlap: number
  split_strategy: 'fixed' | 'paragraph' | 'heading' | 'separator'
  separator: string
  keep_heading: boolean
  clean_whitespace: boolean
  index_status: 'empty' | 'indexing' | 'ready' | 'failed'
  doc_count: number
  segment_count: number
  created_at: string
  updated_at: string
}

export interface KDocument {
  id: string
  dataset_id: string
  name: string
  filename: string
  file_type: string
  file_size: number
  status: 'waiting' | 'parsing' | 'splitting' | 'indexing' | 'completed' | 'failed'
  progress: number
  error?: string
  char_count: number
  chunk_count: number
  created_at: string
}

export interface Segment {
  id: string
  position: number
  content: string
  tokens: number
  heading?: string
  has_embedding: boolean
}

export interface RetrieveHit {
  segment_id: string
  document_id: string
  document_name: string
  content: string
  score: number
  position: number
  heading?: string
}

export interface ToolParam {
  name: string
  type: 'string' | 'number' | 'integer' | 'boolean'
  description?: string
  required?: boolean
  default?: unknown
  location?: 'query' | 'body' | 'path'
}

export interface Tool {
  id: string
  name: string
  tool_key: string
  description: string
  tool_type: 'builtin' | 'http'
  parameters: ToolParam[]
  config: Record<string, any>
  is_builtin: boolean
  enabled: boolean
}

export interface NodeDefinition {
  type: string
  label: string
  description: string
  icon: string
  color: string
  outputs: { name: string; type: string }[]
  branches?: string[]
}

export interface Workflow {
  id: string
  name: string
  description: string
  graph: { nodes: any[]; edges: any[] }
  version: number
  status: string
  run_count: number
  created_at: string
  updated_at: string
}

export interface RunLog {
  id: string
  type: string
  app_id: string
  app_name: string
  user_input: string
  output: string
  status: string
  model_name: string
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens: number
  duration_ms: number
  error?: string
  created_at: string
}

export interface AgentRunDetail {
  run: {
    id: string
    application_id: string
    status: string
    user_input: string
    output: string
    model_name: string
    mode: string
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
    steps_count: number
    tool_calls: number
    duration_ms: number
    error?: string
    created_at: string
  }
  steps: {
    id: string
    step_index: number
    step_type: string
    content: string
    tool_name?: string
    tool_input?: Record<string, any>
    tool_output?: any
    duration_ms: number
  }[]
}

export interface ChatMessageItem {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at?: string
  streaming?: boolean
  error?: string
  meta?: {
    knowledge?: RetrieveHit[]
    toolCalls?: { name: string; arguments: Record<string, any>; output?: any; error?: string; durationMs?: number }[]
    usage?: Record<string, number>
    duration_ms?: number
  }
}

export interface SSEEvent {
  event: string
  data: Record<string, any>
}
