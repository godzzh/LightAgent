<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useDialog,
  useMessage,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { toolApi } from '@/api/knowledge'
import type { Tool, ToolParam } from '@/types'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const builtin = ref<any[]>([])
const custom = ref<Tool[]>([])
const tab = ref('builtin')

const showForm = ref(false)
const saving = ref(false)
const editing = ref<Tool | null>(null)
const form = reactive({
  name: '',
  tool_key: '',
  description: '',
  enabled: true,
  config: {
    url: '',
    method: 'GET',
    headers: '{}',
    query: '{}',
    body: '',
    timeout: 20,
  } as Record<string, any>,
  parameters: [] as ToolParam[],
})

const showTest = ref(false)
const testTarget = ref<{ key: string; id?: string; params: ToolParam[] } | null>(null)
const testArgs = ref<Record<string, any>>({})
const testResult = ref<any>(null)
const testing = ref(false)

const customTotal = computed(() => custom.value.length)

async function load() {
  loading.value = true
  try {
    const [b, c] = await Promise.all([toolApi.builtin(), toolApi.list({ page: 1, page_size: 100 })])
    builtin.value = b
    custom.value = c.items.filter((t) => !t.is_builtin)
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editing.value = null
  form.name = ''
  form.tool_key = ''
  form.description = ''
  form.enabled = true
  form.config = { url: '', method: 'GET', headers: '{}', query: '{}', body: '', timeout: 20 }
  form.parameters = [{ name: 'keyword', type: 'string', description: '查询关键词', required: true, location: 'query' }]
  showForm.value = true
}

function openEdit(t: Tool) {
  editing.value = t
  form.name = t.name
  form.tool_key = t.tool_key
  form.description = t.description
  form.enabled = t.enabled
  form.config = {
    url: t.config?.url || '',
    method: t.config?.method || 'GET',
    headers: JSON.stringify(t.config?.headers || {}, null, 2),
    query: JSON.stringify(t.config?.query || {}, null, 2),
    body: t.config?.body ? JSON.stringify(t.config.body, null, 2) : '',
    timeout: t.config?.timeout || 20,
  }
  form.parameters = [...(t.parameters || [])]
  showForm.value = true
}

function addParam() {
  form.parameters.push({ name: '', type: 'string', description: '', required: false, location: 'query' })
}

function parseJsonSafe(text: string, label: string) {
  if (!text?.trim()) return {}
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`${label} 不是合法 JSON`)
  }
}

async function save() {
  if (!form.name.trim() || !form.tool_key.trim()) {
    message.warning('请填写工具名称与标识')
    return
  }
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(form.tool_key)) {
    message.warning('工具标识只能包含字母、数字、下划线，且不能以数字开头')
    return
  }
  if (!form.config.url.trim()) {
    message.warning('请填写请求地址')
    return
  }
  let config: Record<string, any>
  try {
    config = {
      url: form.config.url,
      method: form.config.method,
      headers: parseJsonSafe(form.config.headers, 'Headers'),
      query: parseJsonSafe(form.config.query, 'Query 参数'),
      body: form.config.body?.trim() ? parseJsonSafe(form.config.body, 'Body') : null,
      timeout: Number(form.config.timeout) || 20,
    }
  } catch (e: any) {
    message.error(e.message)
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name.trim(),
      tool_key: form.tool_key.trim(),
      description: form.description,
      enabled: form.enabled,
      config,
      parameters: form.parameters.filter((p) => p.name),
    }
    if (editing.value) {
      await toolApi.update(editing.value.id, payload as any)
      message.success('已保存')
    } else {
      await toolApi.create(payload as any)
      message.success('工具已创建')
    }
    showForm.value = false
    load()
  } finally {
    saving.value = false
  }
}

function removeTool(t: Tool) {
  dialog.warning({
    title: '删除工具',
    content: `确认删除「${t.name}」？引用它的 Agent 将无法再调用该工具。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await toolApi.remove(t.id)
      message.success('已删除')
      load()
    },
  })
}

function openTest(key: string, params: ToolParam[], id?: string) {
  testTarget.value = { key, id, params: params || [] }
  testArgs.value = {}
  for (const p of params || []) testArgs.value[p.name] = p.default ?? ''
  testResult.value = null
  showTest.value = true
}

async function runTest() {
  if (!testTarget.value) return
  testing.value = true
  testResult.value = null
  try {
    const args = { ...testArgs.value }
    if (testTarget.value.id) testResult.value = await toolApi.test(testTarget.value.id, args)
    else testResult.value = await toolApi.testBuiltin(testTarget.value.key, args)
  } catch (e: any) {
    testResult.value = { error: e.message }
  } finally {
    testing.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="la-page max-w-[1200px]">
    <PageHeader title="工具管理" subtitle="内置工具与自定义 HTTP API 工具，统一注册到 Tool Registry">
      <template #actions>
        <NButton size="small" type="primary" @click="openCreate">
          <template #icon><LaIcon name="plus" :size="14" /></template>
          新建 HTTP 工具
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="la-card p-12 flex justify-center"><NSpin /></div>

    <div v-else class="la-card">
      <NTabs v-model:value="tab" type="line" class="px-4 pt-1">
        <NTabPane name="builtin" :tab="`内置工具 (${builtin.length})`">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pb-4">
            <div v-for="t in builtin" :key="t.tool_key" class="border border-line rounded-lg p-3">
              <div class="flex items-start gap-2.5">
                <span class="w-8 h-8 rounded-lg bg-[rgba(0,122,255,0.09)] text-primary flex items-center justify-center shrink-0">
                  <LaIcon name="tool" :size="15" />
                </span>
                <div class="min-w-0 flex-1">
                  <div class="flex items-center gap-2">
                    <span class="text-[13px] font-medium text-ink">{{ t.name }}</span>
                    <NTag size="tiny" :bordered="false">{{ t.tool_key }}</NTag>
                  </div>
                  <div class="text-[11.5px] text-muted mt-0.5">{{ t.description }}</div>
                  <div class="flex flex-wrap gap-1 mt-1.5">
                    <span
                      v-for="p in t.parameters"
                      :key="p.name"
                      class="text-[10.5px] px-1.5 py-0.5 rounded bg-[#F7F7F9] border border-line text-[#8E8E93] font-mono"
                    >
                      {{ p.name }}{{ p.required ? '*' : '' }}
                    </span>
                  </div>
                </div>
                <NButton size="tiny" quaternary @click="openTest(t.tool_key, t.parameters)">测试</NButton>
              </div>
            </div>
          </div>
        </NTabPane>

        <NTabPane name="custom" :tab="`自定义工具 (${customTotal})`">
          <EmptyState
            v-if="!custom.length"
            icon="globe"
            title="还没有自定义 HTTP 工具"
            description="把任意公网 API 配置成工具，Agent 即可通过 Function Calling 调用（内置 SSRF 防护）"
          >
            <NButton size="small" type="primary" @click="openCreate">新建工具</NButton>
          </EmptyState>
          <div v-else class="divide-y divide-[rgba(118,118,128,0.08)] pb-4">
            <div v-for="t in custom" :key="t.id" class="flex flex-wrap items-center gap-3 py-2.5">
              <span class="w-8 h-8 rounded-lg bg-[rgba(255,149,0,0.12)] text-[#C86A00] flex items-center justify-center">
                <LaIcon name="globe" :size="15" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2">
                  <span class="text-[13px] text-ink">{{ t.name }}</span>
                  <NTag size="tiny" :bordered="false">{{ t.tool_key }}</NTag>
                  <NTag v-if="!t.enabled" size="tiny" :bordered="false" type="warning">已禁用</NTag>
                </div>
                <div class="text-[11.5px] text-muted truncate max-w-lg">
                  {{ t.config?.method }} {{ t.config?.url }}
                </div>
              </div>
              <NButton size="tiny" quaternary @click="openTest(t.tool_key, t.parameters, t.id)">测试</NButton>
              <NButton size="tiny" quaternary @click="openEdit(t)">编辑</NButton>
              <NButton size="tiny" quaternary @click="removeTool(t)">
                <template #icon><LaIcon name="trash" :size="12" /></template>
              </NButton>
            </div>
          </div>
        </NTabPane>
      </NTabs>
    </div>

    <!-- 工具表单 -->
    <NDrawer v-model:show="showForm" :width="620" placement="right">
      <NDrawerContent :title="editing ? '编辑工具' : '新建 HTTP 工具'" closable>
        <div class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <div>
              <div class="text-[12.5px] text-muted mb-1">工具名称</div>
              <NInput v-model:value="form.name" placeholder="例如：天气查询" />
            </div>
            <div>
              <div class="text-[12.5px] text-muted mb-1">工具标识（函数名）</div>
              <NInput v-model:value="form.tool_key" placeholder="get_weather" :disabled="!!editing" />
            </div>
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">工具描述（模型据此决定何时调用）</div>
            <NInput v-model:value="form.description" type="textarea" :rows="2" placeholder="查询指定城市的实时天气" />
          </div>
          <div class="grid grid-cols-[1fr_120px] gap-3">
            <div>
              <div class="text-[12.5px] text-muted mb-1">请求地址（支持变量占位）</div>
              <NInput v-model:value="form.config.url" placeholder="https://api.example.com/weather?city={{city}}" />
            </div>
            <div>
              <div class="text-[12.5px] text-muted mb-1">Method</div>
              <NSelect
                v-model:value="form.config.method"
                :options="['GET', 'POST', 'PUT', 'DELETE'].map((m) => ({ label: m, value: m }))"
              />
            </div>
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Headers（JSON）</div>
            <NInput v-model:value="form.config.headers" type="textarea" :rows="2" class="font-mono" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Query 参数（JSON，支持变量占位）</div>
            <NInput v-model:value="form.config.query" type="textarea" :rows="2" class="font-mono" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Body（JSON，POST/PUT 使用）</div>
            <NInput v-model:value="form.config.body" type="textarea" :rows="3" class="font-mono" />
          </div>

          <div>
            <div class="flex items-center justify-between mb-1">
              <span class="text-[12.5px] text-muted">参数定义（自动转换为 Function Calling Schema）</span>
              <NButton size="tiny" quaternary @click="addParam">
                <template #icon><LaIcon name="plus" :size="12" /></template>
                添加参数
              </NButton>
            </div>
            <div class="space-y-2">
              <div v-for="(p, i) in form.parameters" :key="i" class="flex items-center gap-1.5">
                <NInput v-model:value="p.name" size="tiny" placeholder="参数名" class="!w-[110px]" />
                <NSelect
                  v-model:value="p.type"
                  size="tiny"
                  class="!w-[92px]"
                  :options="['string', 'number', 'integer', 'boolean'].map((t) => ({ label: t, value: t }))"
                />
                <NInput v-model:value="p.description" size="tiny" placeholder="描述" />
                <NSwitch v-model:value="p.required" size="small" />
                <NButton size="tiny" quaternary @click="form.parameters.splice(i, 1)">
                  <template #icon><LaIcon name="close" :size="12" /></template>
                </NButton>
              </div>
            </div>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-[12.5px] text-ink">启用该工具</span>
            <NSwitch v-model:value="form.enabled" size="small" />
          </div>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <NButton size="small" @click="showForm = false">取消</NButton>
            <NButton size="small" type="primary" :loading="saving" @click="save">保存</NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- 测试 -->
    <NModal v-model:show="showTest" preset="card" :title="`测试工具：${testTarget?.key || ''}`" class="!w-[560px]" :bordered="false">
      <div class="space-y-2.5">
        <div v-for="p in testTarget?.params || []" :key="p.name">
          <div class="text-[12.5px] text-muted mb-1">{{ p.name }}（{{ p.type }}{{ p.required ? '，必填' : '' }}）</div>
          <NInput v-model:value="testArgs[p.name]" :placeholder="p.description" />
        </div>
        <div v-if="!(testTarget?.params || []).length" class="text-[12.5px] text-muted">该工具无需参数</div>
        <NButton size="small" type="primary" :loading="testing" @click="runTest">执行测试</NButton>
        <div v-if="testResult" class="bg-[#1C1C1E] text-[#E2E8F0] rounded-lg p-3 text-[11.5px] font-mono max-h-[260px] overflow-auto whitespace-pre-wrap">
{{ JSON.stringify(testResult, null, 2) }}
        </div>
      </div>
    </NModal>
  </div>
</template>
