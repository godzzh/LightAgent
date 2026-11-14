<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NSpin, NSwitch, NTag, useDialog, useMessage } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { appApi } from '@/api/auth'
import type { Application } from '@/types'
import { formatDate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const appId = computed(() => route.params.id as string)
const app = ref<Application | null>(null)
const keys = ref<any[]>([])
const loading = ref(true)
const publishing = ref(false)
const newKey = ref('')

const endpoint = computed(() =>
  app.value?.app_type === 'workflow'
    ? `/api/v1/open/${appId.value}/run`
    : `/api/v1/open/${appId.value}/chat-messages`,
)

const curlExample = computed(() => {
  const key = newKey.value || 'YOUR_API_KEY'
  if (app.value?.app_type === 'workflow') {
    return `curl -X POST http://localhost:8000${endpoint.value} \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"inputs": {"query": "你好"}}'`
  }
  return `curl -X POST http://localhost:8000${endpoint.value} \\
  -H "Authorization: Bearer ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"query": "你好，介绍一下你能做什么", "session_id": "user-001", "stream": false}'`
})

const responseExample = computed(() =>
  app.value?.app_type === 'workflow'
    ? `{
  "code": 0,
  "message": "success",
  "data": {
    "run_id": "9f2c...",
    "outputs": { "answer": "工作流输出" },
    "usage": { "total_tokens": 328 },
    "duration_ms": 1832
  }
}`
    : `{
  "code": 0,
  "message": "success",
  "data": {
    "run_id": "9f2c...",
    "session_id": "user-001",
    "answer": "我是客服助手，可以……",
    "usage": { "prompt_tokens": 210, "completion_tokens": 96, "total_tokens": 306 },
    "duration_ms": 1520
  }
}`,
)

async function load() {
  loading.value = true
  try {
    app.value = await appApi.detail(appId.value)
    keys.value = await appApi.keys(appId.value)
  } finally {
    loading.value = false
  }
}

async function publish() {
  publishing.value = true
  try {
    const res = await appApi.publish(appId.value, { api_enabled: true, create_key: true })
    if (res.api_key) newKey.value = res.api_key
    message.success('发布成功')
    await load()
    if (newKey.value) {
      dialog.success({
        title: 'API Key 已生成（仅展示一次）',
        content: newKey.value,
        positiveText: '我已保存',
      })
    }
  } finally {
    publishing.value = false
  }
}

async function unpublish() {
  await appApi.unpublish(appId.value)
  message.success('已取消发布')
  load()
}

async function createKey() {
  const res = await appApi.createKey(appId.value)
  newKey.value = res.api_key
  message.success('已生成新密钥')
  dialog.success({ title: 'API Key（仅展示一次）', content: res.api_key, positiveText: '我已保存' })
  load()
}

async function copy(text: string) {
  await navigator.clipboard.writeText(text)
  message.success('已复制')
}

function toggleApi(v: boolean) {
  if (!app.value) return
  app.value.api_enabled = v
  appApi.publish(appId.value, { api_enabled: v, create_key: false }).then(load)
}

onMounted(load)
</script>

<template>
  <div class="la-page max-w-[1100px]">
    <PageHeader
      :title="`发布设置 · ${app?.name || ''}`"
      subtitle="发布后即可通过独立 API 被第三方系统调用"
    >
      <template #actions>
        <NButton size="small" @click="router.push(`/applications/${appId}/${app?.app_type === 'workflow' ? 'publish' : 'agent'}`)">
          返回调试
        </NButton>
        <NButton v-if="app?.status === 'published'" size="small" @click="unpublish">取消发布</NButton>
        <NButton size="small" type="primary" :loading="publishing" @click="publish">
          {{ app?.status === 'published' ? '重新发布（生成快照）' : '发布应用' }}
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="la-card p-12 flex justify-center"><NSpin /></div>

    <template v-else-if="app">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
        <div class="la-card p-4">
          <div class="text-[11.5px] text-muted">发布状态</div>
          <div class="mt-1.5"><StatusTag :status="app.status" /></div>
        </div>
        <div class="la-card p-4">
          <div class="text-[11.5px] text-muted">API 开关</div>
          <div class="flex items-center gap-2 mt-1.5">
            <NSwitch :value="app.api_enabled" size="small" :disabled="app.status !== 'published'" @update:value="toggleApi" />
            <span class="text-[12px] text-[rgba(60,60,67,0.7)]">{{ app.api_enabled ? '已开启' : '已关闭' }}</span>
          </div>
        </div>
        <div class="la-card p-4">
          <div class="text-[11.5px] text-muted">最近发布</div>
          <div class="text-[13px] text-ink mt-1.5">{{ formatDate(app.published_at) }}</div>
        </div>
      </div>

      <!-- API 端点 -->
      <div class="la-card p-4 mb-3">
        <div class="text-[13.5px] font-medium text-ink mb-2">API 端点</div>
        <div class="flex items-center gap-2 bg-[#F7F7F9] border border-line rounded-lg px-3 py-2">
          <NTag size="small" :bordered="false" type="info">{{ app.app_type === 'workflow' ? 'POST' : 'POST' }}</NTag>
          <code class="text-[12px] text-[#1C1C1E] flex-1 break-all">http://localhost:8000{{ endpoint }}</code>
          <NButton size="tiny" quaternary @click="copy(`http://localhost:8000${endpoint}`)">
            <template #icon><LaIcon name="copy" :size="13" /></template>
          </NButton>
        </div>
        <div class="text-[11.5px] text-muted mt-2">
          鉴权方式：请求头 <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">Authorization: Bearer &lt;API_KEY&gt;</code>
          或 <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">X-API-Key</code>。流式调用请传
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">"stream": true</code>。
        </div>
      </div>

      <!-- API Key -->
      <div class="la-card p-4 mb-3">
        <div class="flex items-center justify-between mb-2">
          <div class="text-[13.5px] font-medium text-ink">API 访问密钥</div>
          <NButton size="tiny" @click="createKey">
            <template #icon><LaIcon name="plus" :size="12" /></template>
            生成新密钥
          </NButton>
        </div>
        <div v-if="!keys.length" class="text-[12.5px] text-muted">
          暂无密钥。发布应用或点击「生成新密钥」创建，明文仅在创建时展示一次。
        </div>
        <div v-else class="divide-y divide-[rgba(118,118,128,0.08)]">
          <div v-for="k in keys" :key="k.id" class="flex items-center gap-3 py-2">
            <LaIcon name="key" :size="14" class="text-[#C86A00]" />
            <span class="text-[12.5px] text-ink">{{ k.name }}</span>
            <code class="text-[11.5px] text-muted font-mono">{{ k.key_prefix }}••••••</code>
            <span class="text-[11px] text-muted">最近使用：{{ formatDate(k.last_used_at) }}</span>
            <div class="flex-1"></div>
            <NButton
              size="tiny"
              quaternary
              @click="appApi.deleteKey(appId, k.id).then(() => ((keys = keys.filter((x) => x.id !== k.id)), message.success('已删除')))"
            >
              <template #icon><LaIcon name="trash" :size="12" /></template>
            </NButton>
          </div>
        </div>
      </div>

      <!-- 调用示例 -->
      <div class="la-card p-4">
        <div class="text-[13.5px] font-medium text-ink mb-2">调用示例</div>
        <div class="text-[11.5px] text-muted mb-1">请求</div>
        <pre class="bg-[#1C1C1E] text-[#E2E8F0] rounded-lg p-3 text-[11.5px] overflow-x-auto font-mono">{{ curlExample }}</pre>
        <div class="text-[11.5px] text-muted mt-3 mb-1">响应（非流式）</div>
        <pre class="bg-[#F7F7F9] border border-line text-[#1C1C1E] rounded-lg p-3 text-[11.5px] overflow-x-auto font-mono">{{ responseExample }}</pre>

        <div class="mt-3 text-[11.5px] text-muted leading-5">
          流式响应使用标准 SSE，事件包括
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">run_started</code>
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">token</code>
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">tool_call</code>
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">tool_result</code>
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">run_completed</code>
          <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">run_error</code>。
          客户端断开时后端会自动取消执行并落库。
        </div>
      </div>
    </template>
  </div>
</template>
