<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NDropdown, NInput, NSpin, NTooltip, useMessage } from 'naive-ui'
import ConfigPanel from '@/components/agent/ConfigPanel.vue'
import ChatMessage from '@/components/agent/ChatMessage.vue'
import RunDetailPanel, { type RunSnapshot } from '@/components/agent/RunDetailPanel.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { appApi } from '@/api/auth'
import { agentApi } from '@/api/agent'
import { modelApi, knowledgeApi, toolApi } from '@/api/knowledge'
import type { AgentConfig, Application, ChatMessageItem, Dataset, ModelConfig, Tool } from '@/types'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const appId = computed(() => route.params.id as string)
const loading = ref(true)
const saving = ref(false)
const app = ref<Application | null>(null)
const config = ref<AgentConfig | null>(null)
const models = ref<ModelConfig[]>([])
const tools = ref<Tool[]>([])
const datasets = ref<Dataset[]>([])
const dirty = ref(false)

const input = ref('')
const sending = ref(false)
const messages = ref<ChatMessageItem[]>([])
const sessionId = ref<string>(`dbg-${Date.now()}`)
const run = ref<RunSnapshot | null>(null)
const showRunPanel = ref(true)
const scrollEl = ref<HTMLDivElement | null>(null)
let streamHandle: { abort: () => void } | null = null

const DEFAULT_CONFIG: AgentConfig = {
  system_prompt: '你是一个乐于助人的 AI 助手。',
  user_prompt: '{{query}}',
  welcome_message: '你好，我是你的智能助手，有什么可以帮你？',
  opening_questions: [],
  mode: 'function_calling',
  model_config_id: null,
  temperature: 0.7,
  top_p: 1,
  max_tokens: 2048,
  max_steps: 8,
  max_tool_calls: 6,
  max_context_messages: 20,
  enable_memory: true,
  enable_tools: true,
  enable_knowledge: true,
  tools: [],
  dataset_ids: [],
  knowledge_top_k: 4,
  knowledge_threshold: 0.3,
  variables: [],
}

const currentModel = computed(() => models.value.find((m) => m.id === config.value?.model_config_id))
const runPanelConfig = computed(() => ({
  model_name: currentModel.value?.model_name,
  mode: config.value?.mode,
}))

async function load() {
  loading.value = true
  try {
    const [detail, mdl, tls, ds] = await Promise.all([
      appApi.detail(appId.value),
      modelApi.available(),
      toolApi.list({ page: 1, page_size: 100 }),
      knowledgeApi.datasets({ page: 1, page_size: 100 }),
    ])
    app.value = detail
    config.value = { ...DEFAULT_CONFIG, ...(detail.config || {}) }
    if (!config.value.model_config_id) config.value.model_config_id = detail.model_config_id || null
    models.value = mdl
    tools.value = tls.items
    datasets.value = ds.items
  } finally {
    loading.value = false
  }
}

watch(
  () => config.value,
  () => {
    if (!loading.value) dirty.value = true
  },
  { deep: true },
)

async function save() {
  if (!config.value) return
  saving.value = true
  try {
    await appApi.update(appId.value, { config: config.value })
    dirty.value = false
    message.success('配置已保存')
  } finally {
    saving.value = false
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (scrollEl.value) scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  })
}

function pushAssistant(): ChatMessageItem {
  const msg: ChatMessageItem = { role: 'assistant', content: '', streaming: true, meta: { toolCalls: [] } }
  messages.value.push(msg)
  return msg
}

function send() {
  const query = input.value.trim()
  if (!query || sending.value || !config.value) return
  if (!config.value.model_config_id) {
    message.warning('请先在右侧配置中选择模型')
    return
  }
  input.value = ''
  messages.value.push({ role: 'user', content: query, created_at: new Date().toISOString() })
  const assistant = pushAssistant()
  sending.value = true
  run.value = { status: 'running', model: currentModel.value?.model_name, mode: config.value.mode, toolCalls: [], knowledge: [] }
  scrollToBottom()

  streamHandle = agentApi.chatStream(
    appId.value,
    { query, session_id: sessionId.value },
    {
      onEvent: (ev) => {
        const data = ev.data || {}
        if (ev.event === 'run_started') {
          run.value = { ...(run.value || { status: 'running' }), runId: data.run_id, status: 'running' }
        } else if (ev.event === 'knowledge') {
          const chunks = data.chunks || []
          assistant.meta = { ...(assistant.meta || {}), knowledge: chunks }
          if (run.value) run.value.knowledge = chunks
        } else if (ev.event === 'token') {
          assistant.content += data.content || ''
          scrollToBottom()
        } else if (ev.event === 'tool_call') {
          const item = { name: data.name, arguments: data.arguments || {}, durationMs: 0 }
          assistant.meta = assistant.meta || {}
          assistant.meta.toolCalls = [...(assistant.meta.toolCalls || []), item]
          if (run.value) run.value.toolCalls = [...(run.value.toolCalls || []), item]
        } else if (ev.event === 'tool_result') {
          const list = assistant.meta?.toolCalls || []
          const target = [...list].reverse().find((t) => t.name === data.name && t.output === undefined)
          if (target) {
            target.output = data.output
            target.error = data.error
            target.durationMs = data.duration_ms
          }
          if (run.value?.toolCalls) run.value.toolCalls = [...list]
        } else if (ev.event === 'run_completed') {
          assistant.streaming = false
          assistant.meta = {
            ...(assistant.meta || {}),
            usage: data.usage,
            duration_ms: data.duration_ms,
          }
          if (run.value) {
            run.value.status = 'succeeded'
            run.value.usage = data.usage
            run.value.durationMs = data.duration_ms
          }
          scrollToBottom()
        } else if (ev.event === 'run_error' || ev.event === 'run_failed') {
          assistant.streaming = false
          assistant.error = data.message || '执行失败'
          if (run.value) {
            run.value.status = 'failed'
            run.value.error = data.message
          }
          message.error(data.message || '执行失败')
        }
      },
      onError: (e) => {
        assistant.streaming = false
        assistant.error = e.message
        if (run.value) {
          run.value.status = 'failed'
          run.value.error = e.message
        }
        message.error(e.message)
      },
      onClose: () => {
        assistant.streaming = false
        sending.value = false
        streamHandle = null
      },
    },
  )
}

function stop() {
  streamHandle?.abort()
  sending.value = false
  const last = messages.value[messages.value.length - 1]
  if (last?.streaming) {
    last.streaming = false
    if (!last.content) last.content = '_（已停止生成）_'
  }
}

function regenerate() {
  const lastUser = [...messages.value].reverse().find((m) => m.role === 'user')
  if (!lastUser || sending.value) return
  const lastIndex = messages.value.findLastIndex((m) => m.role === 'assistant')
  if (lastIndex >= 0) messages.value.splice(lastIndex, 1)
  input.value = lastUser.content
  const idx = messages.value.findLastIndex((m) => m.role === 'user')
  if (idx >= 0) messages.value.splice(idx, 1)
  send()
}

function clearChat() {
  stop()
  messages.value = []
  run.value = null
  sessionId.value = `dbg-${Date.now()}`
}

function copySession() {
  navigator.clipboard.writeText(sessionId.value)
  message.success('会话 ID 已复制')
}

function onEnter(e: KeyboardEvent) {
  if (e.shiftKey) return
  e.preventDefault()
  send()
}

const moreOptions = [
  { label: '重新生成', key: 'regen' },
  { label: '复制会话 ID', key: 'session' },
  { label: '查看运行日志', key: 'logs' },
]

function onMore(key: string) {
  if (key === 'regen') regenerate()
  else if (key === 'session') copySession()
  else if (key === 'logs') router.push({ name: 'logs', query: { app: appId.value } })
}

onMounted(load)
</script>

<template>
  <div class="h-[calc(100vh-52px)] flex overflow-hidden bg-surface">
    <div v-if="loading" class="flex-1 flex items-center justify-center"><NSpin /></div>

    <template v-else-if="app && config">
      <!-- 左：配置 -->
      <div class="w-[380px] shrink-0 border-r border-line bg-white">
        <ConfigPanel
          :config="config"
          :models="models"
          :tools="tools"
          :datasets="datasets"
          :saving="saving"
          :dirty="dirty"
          @update:config="(v) => (config = v)"
          @save="save"
        />
      </div>

      <!-- 中：对话 -->
      <div class="flex-1 flex flex-col min-w-0">
        <div class="la-glass h-[52px] shrink-0 border-b px-4 flex items-center gap-2">
          <span class="text-[14.5px] font-semibold text-ink truncate tracking-tight">{{ app.name }}</span>
          <StatusTag :status="app.status" />
          <span class="text-[11.5px] text-muted ml-0.5">
            {{ currentModel?.display_name || '未选择模型' }}
          </span>
          <div class="flex-1"></div>
          <NTooltip>
            <template #trigger>
              <NButton size="tiny" quaternary @click="showRunPanel = !showRunPanel">
                <template #icon><LaIcon name="sliders" :size="14" /></template>
              </NButton>
            </template>
            {{ showRunPanel ? '隐藏运行详情' : '显示运行详情' }}
          </NTooltip>
          <NButton size="tiny" quaternary @click="clearChat">
            <template #icon><LaIcon name="trash" :size="14" /></template>
            清空
          </NButton>
          <NDropdown :options="moreOptions" @select="onMore">
            <NButton size="tiny" quaternary>
              <template #icon><LaIcon name="more" :size="14" /></template>
            </NButton>
          </NDropdown>
          <NButton size="tiny" @click="router.push(`/applications/${app.id}/publish`)">
            <template #icon><LaIcon name="globe" :size="14" /></template>
            发布
          </NButton>
        </div>

        <!-- 消息区 -->
        <div ref="scrollEl" class="flex-1 overflow-y-auto px-5 py-5 space-y-4">
          <div v-if="!messages.length" class="h-full flex flex-col items-center justify-center text-center">
            <div
              class="w-[56px] h-[56px] rounded-[16px] text-white flex items-center justify-center mb-4"
              style="background: linear-gradient(160deg, #4ba3ff 0%, #007aff 100%); box-shadow: 0 6px 20px -8px rgba(0, 122, 255, 0.6)"
            >
              <LaIcon name="sparkles" :size="26" :stroke-width="2" />
            </div>
            <div class="text-[16px] font-semibold text-ink tracking-tight">{{ app.name }}</div>
            <div class="text-[13px] text-muted mt-1.5 max-w-md leading-relaxed">
              {{ config.welcome_message || '开始对话，体验你的智能体' }}
            </div>
            <div v-if="config.opening_questions?.length" class="flex flex-wrap justify-center gap-2 mt-5 max-w-lg">
              <button
                v-for="q in config.opening_questions"
                :key="q"
                class="ios-press text-[12.5px] px-3.5 py-2 rounded-full bg-white border border-line text-[rgba(60,60,67,0.8)] hover:text-primary hover:border-[rgba(0,122,255,0.4)]"
                @click="((input = q), send())"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <ChatMessage v-for="(m, i) in messages" :key="m.id || i" :message="m" />
        </div>

        <!-- 输入区：iOS 消息输入条 -->
        <div class="shrink-0 px-4 py-3 border-t border-line" style="background: rgba(255, 255, 255, 0.8)">
          <div
            class="rounded-[20px] bg-white transition-all"
            style="border: 1px solid rgba(60, 60, 67, 0.13); box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03)"
          >
            <NInput
              v-model:value="input"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              placeholder="输入问题，Enter 发送 / Shift+Enter 换行"
              :bordered="false"
              :disabled="sending"
              @keydown.enter="onEnter"
            />
            <div class="flex items-center justify-between px-3 pb-2.5">
              <div class="flex items-center gap-3 text-[11px] text-muted">
                <span class="font-mono opacity-70">会话 {{ sessionId.slice(0, 10) }}</span>
                <span v-if="config.enable_tools" class="flex items-center gap-1">
                  <LaIcon name="tool" :size="11" />{{ config.tools?.length || 0 }} 工具
                </span>
                <span v-if="config.enable_knowledge" class="flex items-center gap-1">
                  <LaIcon name="book" :size="11" />{{ config.dataset_ids?.length || 0 }} 知识库
                </span>
              </div>
              <div class="flex items-center gap-2">
                <NButton v-if="sending" size="tiny" @click="stop">
                  <template #icon><LaIcon name="stop" :size="13" /></template>
                  停止
                </NButton>
                <NButton
                  v-else
                  size="small"
                  type="primary"
                  circle
                  :disabled="!input.trim()"
                  style="width: 32px; height: 32px; min-width: 32px"
                  @click="send"
                >
                  <template #icon><LaIcon name="send" :size="15" /></template>
                </NButton>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右：运行详情 -->
      <div v-if="showRunPanel" class="w-[300px] shrink-0 border-l border-line bg-white">
        <RunDetailPanel :run="run" :config="runPanelConfig" />
      </div>
    </template>
  </div>
</template>
