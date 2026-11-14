<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import {
  NButton,
  NInput,
  NModal,
  NSpin,
  NTooltip,
  useMessage,
} from 'naive-ui'
import WorkflowNode from '@/components/workflow/WorkflowNode.vue'
import NodeConfigPanel from '@/components/workflow/NodeConfigPanel.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { workflowApi } from '@/api/workflows'
import { modelApi, knowledgeApi } from '@/api/knowledge'
import type { Dataset, ModelConfig, NodeDefinition } from '@/types'
import { formatDuration } from '@/utils/format'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
import '@vue-flow/minimap/dist/style.css'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const workflowId = computed(() => route.params.id as string)
// @ts-ignore Vue Flow 的泛型在严格模式下推导过深，运行时无影响
// 画布实例通过组件事件与内置 fit-view-on-init 控制，避免在父级提前创建 store

const loading = ref(true)
const saving = ref(false)
const running = ref(false)
const name = ref('')
const description = ref('')
const nodes = ref<any[]>([])
const edges = ref<any[]>([])
const selectedId = ref<string | null>(null)
const definitions = ref<NodeDefinition[]>([])
const models = ref<ModelConfig[]>([])
const datasets = ref<Dataset[]>([])
const showRunPanel = ref(false)
const showInputs = ref(false)
const runInputs = reactive<Record<string, string>>({})
const runEvents = ref<{ event: string; text: string; time: string }[]>([])
const runResult = ref<any>(null)
const runError = ref('')
const runDuration = ref(0)
const history = ref<string[]>([])
const historyIndex = ref(-1)
let streamHandle: { abort: () => void } | null = null

const selectedNode = computed(() => nodes.value.find((n) => n.id === selectedId.value) || null)
const selectedDef = computed(() => definitions.value.find((d) => d.type === selectedNode.value?.type))

const startNode = computed(() => nodes.value.find((n) => n.type === 'start'))
const startParams = computed<{ name: string; type: string; required: boolean; default: any; description?: string }[]>(
  () => (startNode.value?.data?.params as any[]) || [],
)

/** 上游变量（简化：取所有其他节点的输出字段） */
const upstreamVars = computed(() => {
  const list: { label: string; value: string }[] = []
  for (const n of nodes.value) {
    if (n.id === selectedId.value) continue
    const def = definitions.value.find((d) => d.type === n.type)
    const outs = def?.outputs?.length ? def.outputs : [{ name: 'text', type: 'string' }]
    for (const o of outs) list.push({ label: `${n.data?.title || n.id}.${o.name}`, value: `${n.id}.${o.name}` })
    if (n.type === 'start') {
      for (const p of (n.data?.params as any[]) || []) {
        list.push({ label: `start.${p.name}`, value: `start.${p.name}` })
      }
    }
  }
  return list
})

function uid(prefix: string) {
  let i = 1
  while (nodes.value.some((n) => n.id === `${prefix}_${i}`)) i++
  return `${prefix}_${i}`
}

/** 新建连线（Vue Flow 通过 onConnect 事件抛出连接参数） */
function onConnect(connection: any) {
  const id = `e_${connection.source}_${connection.target}_${Math.random().toString(36).slice(2, 6)}`
  edges.value = [...edges.value, { ...connection, id, animated: false }]
  snapshot()
}

function snapshot() {
  const serialized = JSON.stringify({ nodes: serializeNodes(), edges })
  if (history.value[historyIndex.value] === serialized) return
  history.value = history.value.slice(0, historyIndex.value + 1)
  history.value.push(serialized)
  if (history.value.length > 40) history.value.shift()
  historyIndex.value = history.value.length - 1
}

function serializeNodes() {
  return nodes.value.map((n) => ({
    id: n.id,
    type: n.type,
    position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
    data: cleanData(n.data || {}),
  }))
}

function cleanData(data: Record<string, any>) {
  const out: Record<string, any> = {}
  for (const [k, v] of Object.entries(data)) if (!k.startsWith('__')) out[k] = v
  return out
}

function applySnapshot(json: string) {
  const parsed = JSON.parse(json)
  nodes.value = parsed.nodes.map(decorate)
  edges.value = parsed.edges
}

function decorate(node: any): any {
  const def = definitions.value.find((d) => d.type === node.type)
  return {
    ...node,
    type: 'la',
    data: {
      ...node.data,
      __label: def?.label,
      __icon: def?.icon,
      __color: def?.color,
      __typeLabel: def?.label,
      __desc: node.data?.title || def?.label,
    },
  }
}

function undo() {
  if (historyIndex.value <= 0) return
  historyIndex.value -= 1
  applySnapshot(history.value[historyIndex.value])
}

function redo() {
  if (historyIndex.value >= history.value.length - 1) return
  historyIndex.value += 1
  applySnapshot(history.value[historyIndex.value])
}

function addNode(def: NodeDefinition) {
  const id = uid(def.type)
  const position = { x: 260 + Math.random() * 120, y: 120 + nodes.value.length * 40 }
  const data: Record<string, any> = { title: def.label }
  if (def.type === 'llm') {
    data.user_prompt = '{{start.query}}'
  } else if (def.type === 'answer') {
    data.answer = ''
  } else if (def.type === 'condition') {
    data.operator = 'contains'
  } else if (def.type === 'variable') {
    data.name = 'my_var'
  } else if (def.type === 'code') {
    data.expression = ''
    data.output_key = 'result'
  } else if (def.type === 'knowledge') {
    data.top_k = 4
    data.threshold = 0.3
  } else if (def.type === 'http') {
    data.method = 'GET'
    data.timeout = 20
  }
  nodes.value.push(decorate({ id, type: def.type, position, data }))
  selectedId.value = id
  nextTick(() => snapshot())
}

function removeSelected() {
  if (!selectedId.value) return
  nodes.value = nodes.value.filter((n) => n.id !== selectedId.value)
  edges.value = edges.value.filter((e) => e.source !== selectedId.value && e.target !== selectedId.value)
  selectedId.value = null
  snapshot()
}

function updateNodeData(data: Record<string, any>) {
  if (!selectedNode.value) return
  selectedNode.value.data = { ...selectedNode.value.data, ...data }
  snapshot()
}

/** 简易自动布局：按 BFS 层级横向排布 */
function autoLayout() {
  const adj = new Map<string, string[]>()
  const indeg = new Map<string, number>()
  nodes.value.forEach((n) => {
    adj.set(n.id, [])
    indeg.set(n.id, 0)
  })
  edges.value.forEach((e) => {
    adj.get(e.source)?.push(e.target)
    indeg.set(e.target, (indeg.get(e.target) || 0) + 1)
  })
  const queue = nodes.value.filter((n) => (indeg.get(n.id) || 0) === 0).map((n) => n.id)
  const level = new Map<string, number>()
  queue.forEach((id) => level.set(id, 0))
  while (queue.length) {
    const cur = queue.shift()!
    for (const nxt of adj.get(cur) || []) {
      level.set(nxt, Math.max(level.get(nxt) || 0, (level.get(cur) || 0) + 1))
      indeg.set(nxt, (indeg.get(nxt) || 0) - 1)
      if ((indeg.get(nxt) || 0) === 0) queue.push(nxt)
    }
  }
  const counters = new Map<number, number>()
  nodes.value.forEach((n) => {
    const lv = level.get(n.id) || 0
    const idx = counters.get(lv) || 0
    counters.set(lv, idx + 1)
    n.position = { x: 80 + lv * 280, y: 80 + idx * 150 }
  })
  snapshot()
}

async function load() {
  loading.value = true
  try {
    const [wf, defs, mdl, ds] = await Promise.all([
      workflowApi.detail(workflowId.value),
      workflowApi.nodeDefinitions(),
      modelApi.available(),
      knowledgeApi.datasets({ page: 1, page_size: 100 }),
    ])
    definitions.value = defs
    models.value = mdl
    datasets.value = ds.items
    name.value = wf.name
    description.value = wf.description
    nodes.value = (wf.graph?.nodes || []).map(decorate)
    edges.value = (wf.graph?.edges || []).map((e: any) => ({ ...e, animated: false }))
    snapshot()
  } finally {
    loading.value = false
  }
}

function buildGraph() {
  return { nodes: serializeNodes(), edges: edges.value.map((e) => ({ id: e.id, source: e.source, target: e.target, sourceHandle: e.sourceHandle ?? null })) }
}

async function save(silent = false) {
  saving.value = true
  try {
    await workflowApi.update(workflowId.value, {
      name: name.value,
      description: description.value,
      graph: buildGraph(),
    })
    if (!silent) message.success('已保存')
  } finally {
    saving.value = false
  }
}

async function validate() {
  const res = await workflowApi.validate(workflowId.value)
  if (res.ok) message.success('图校验通过')
  else message.error(res.errors.join('；'))
}

function openRun() {
  runInputs__reset()
  runResult.value = null
  runError.value = ''
  runEvents.value = []
  showInputs.value = true
}

function runInputs__reset() {
  for (const k of Object.keys(runInputs)) delete runInputs[k]
  for (const p of startParams.value) runInputs[p.name] = String(p.default ?? '')
}

function resetStatus() {
  nodes.value.forEach((n) => {
    if (n.data) n.data.__status = undefined
  })
}

async function startRun() {
  showInputs.value = false
  showRunPanel.value = true
  resetStatus()
  runEvents.value = []
  runResult.value = null
  runError.value = ''
  runDuration.value = 0
  running.value = true
  await save(true)

  const inputs: Record<string, any> = {}
  for (const p of startParams.value) {
    const raw = runInputs[p.name]
    inputs[p.name] = p.type === 'number' ? Number(raw) : p.type === 'boolean' ? raw === 'true' : raw
  }

  const started = Date.now()
  streamHandle = workflowApi.runStream(
    workflowId.value,
    inputs,
    {
      onEvent: (ev) => {
        const d = ev.data || {}
        const push = (text: string) => runEvents.value.push({ event: ev.event, text, time: new Date().toLocaleTimeString('zh-CN') })
        const node = nodes.value.find((n) => n.id === d.node_id)
        if (ev.event === 'node_started') {
          if (node) node.data.__status = 'running'
          push(`开始执行：${d.title || d.node_id}`)
        } else if (ev.event === 'node_completed') {
          if (node) node.data.__status = 'succeeded'
          push(`完成：${d.title || d.node_id}（${d.duration_ms}ms）`)
        } else if (ev.event === 'node_failed') {
          if (node) node.data.__status = 'failed'
          push(`失败：${d.title || d.node_id} — ${d.error}`)
        } else if (ev.event === 'node_skipped') {
          if (node) node.data.__status = 'skipped'
          push(`跳过：${d.title || d.node_id}`)
        } else if (ev.event === 'run_started') {
          push(`运行开始（run_id=${d.run_id}）`)
        } else if (ev.event === 'run_completed') {
          runResult.value = d
          runDuration.value = d.duration_ms || Date.now() - started
          push('运行完成')
        } else if (ev.event === 'run_error' || ev.event === 'run_failed') {
          runError.value = d.message || '运行失败'
          push(`错误：${runError.value}`)
          message.error(runError.value)
        }
      },
      onError: (e) => {
        runError.value = e.message
        running.value = false
        message.error(e.message)
      },
      onClose: () => {
        running.value = false
        streamHandle = null
      },
    },
  )
}

function stopRun() {
  streamHandle?.abort()
  running.value = false
  message.info('已中止运行')
}

watch(selectedId, (v) => {
  if (v) showRunPanel.value = showRunPanel.value
})

onMounted(load)
</script>

<template>
  <div class="h-[calc(100vh-52px)] flex flex-col bg-surface overflow-hidden">
    <!-- 工具栏 -->
    <div class="la-glass h-[52px] shrink-0 border-b px-3 flex items-center gap-2 z-10">
      <NButton size="tiny" quaternary @click="router.push('/workflows')">
        <template #icon><LaIcon name="chevronLeft" :size="14" /></template>
        返回
      </NButton>
      <NInput v-model:value="name" size="small" class="!w-[220px]" placeholder="工作流名称" />
      <div class="flex-1"></div>
      <NTooltip><template #trigger>
        <NButton size="tiny" quaternary :disabled="historyIndex <= 0" @click="undo">
          <template #icon><LaIcon name="chevronLeft" :size="13" /></template>
        </NButton>
      </template>撤销</NTooltip>
      <NTooltip><template #trigger>
        <NButton size="tiny" quaternary :disabled="historyIndex >= history.length - 1" @click="redo">
          <template #icon><LaIcon name="chevronRight" :size="13" /></template>
        </NButton>
      </template>重做</NTooltip>
      <NButton size="tiny" quaternary @click="autoLayout">
        <template #icon><LaIcon name="flow" :size="13" /></template>
        自动布局
      </NButton>
      <NButton size="tiny" quaternary @click="validate">校验</NButton>
      <NButton size="small" :loading="saving" @click="save()">保存</NButton>
      <NButton size="small" type="primary" :loading="running" @click="openRun">
        <template #icon><LaIcon name="play" :size="13" /></template>
        运行
      </NButton>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center"><NSpin /></div>

    <div v-else class="flex-1 flex min-h-0">
      <!-- 节点面板 -->
      <aside class="w-[196px] shrink-0 bg-white border-r border-line overflow-y-auto">
        <div class="la-section-label px-3 pt-3 pb-2">节点</div>
        <div class="px-2.5 pb-3 space-y-1.5">
          <button
            v-for="d in definitions"
            :key="d.type"
            class="ios-press w-full flex items-center gap-2 px-2.5 py-2 rounded-[11px] text-left"
            style="background: #fff; border: 0.5px solid rgba(60, 60, 67, 0.13); box-shadow: 0 1px 1px rgba(0, 0, 0, 0.03)"
            @click="addNode(d)"
          >
            <span
              class="w-[22px] h-[22px] rounded-[7px] flex items-center justify-center text-white shrink-0"
              :style="{
                background: d.color,
                boxShadow: 'inset 0 0.5px 0 rgba(255,255,255,0.3), 0 1px 2px rgba(0,0,0,0.12)',
              }"
            >
              <LaIcon :name="d.icon" :size="12" :stroke-width="2" />
            </span>
            <span class="text-[12.5px] text-ink truncate">{{ d.label }}</span>
          </button>
        </div>
        <div class="px-3 py-2.5 border-t border-line text-[11px] text-muted leading-[1.6]">
          点击添加节点，拖拽连线。<br />Delete 删除选中节点。
        </div>
      </aside>

      <!-- 画布 -->
      <div class="flex-1 min-w-0 relative" @keydown.delete="removeSelected">
        <VueFlow
          v-model:nodes="nodes"
          v-model:edges="edges"
          :default-viewport="{ zoom: 0.95 }"
          :min-zoom="0.2"
          :max-zoom="2"
          fit-view-on-init
          @node-click="(e: any) => (selectedId = e.node.id)"
          @node-drag-stop="snapshot"
          @connect="onConnect"
          @pane-click="selectedId = null"
          @nodes-delete="snapshot"
        >
          <template #node-la="props">
            <WorkflowNode v-bind="props" />
          </template>
          <Background :gap="16" :size="1" color="rgba(60,60,67,0.13)" />
          <Controls />
          <MiniMap pannable zoomable />
        </VueFlow>

        <!-- 运行面板 -->
        <div
          v-if="showRunPanel"
          class="absolute bottom-3 left-3 right-3 bg-white overflow-hidden"
          style="border-radius: 16px; border: 0.5px solid rgba(60, 60, 67, 0.13); box-shadow: 0 8px 32px -12px rgba(0, 0, 0, 0.22)"
        >
          <div class="h-10 px-3.5 flex items-center gap-2 border-b border-line" style="background: rgba(255,255,255,0.9)">
            <span class="text-[12.5px] font-semibold text-ink tracking-tight">运行记录</span>
            <span v-if="running" class="la-pill" style="background: rgba(0,122,255,0.12); color: #007aff">
              <span class="w-[5px] h-[5px] rounded-full" style="background: currentColor; animation: la-pulse-dot 1.2s ease-in-out infinite"></span>
              执行中
            </span>
            <span v-else-if="runResult" class="la-pill" style="background: rgba(52,199,89,0.14); color: #248a3d">
              完成 · {{ formatDuration(runDuration) }}
            </span>
            <span v-else-if="runError" class="la-pill" style="background: rgba(255,59,48,0.12); color: #d70015">失败</span>
            <div class="flex-1"></div>
            <NButton v-if="running" size="tiny" @click="stopRun">中止</NButton>
            <NButton size="tiny" quaternary @click="showRunPanel = false">
              <template #icon><LaIcon name="close" :size="12" /></template>
            </NButton>
          </div>
          <div class="grid grid-cols-[1fr_320px] max-h-[220px]">
            <div class="overflow-y-auto px-3.5 py-2.5 space-y-1">
              <div v-for="(e, i) in runEvents" :key="i" class="flex items-start gap-2 text-[11.5px]">
                <span class="text-muted font-mono shrink-0 opacity-70">{{ e.time }}</span>
                <span
                  :style="
                    e.event === 'node_failed' || e.event === 'run_error'
                      ? 'color:#D70015'
                      : e.event === 'node_completed'
                        ? 'color:#248A3D'
                        : 'color:rgba(60,60,67,0.72)'
                  "
                >
                  {{ e.text }}
                </span>
              </div>
              <div v-if="!runEvents.length" class="text-[11.5px] text-muted">暂无事件</div>
            </div>
            <div class="border-l border-line p-3 overflow-y-auto" style="background: rgba(118, 118, 128, 0.05)">
              <div class="text-[11px] text-muted mb-1.5">最终输出</div>
              <pre v-if="runResult" class="text-[11px] font-mono text-ink whitespace-pre-wrap break-all">{{ JSON.stringify(runResult.outputs, null, 2) }}</pre>
              <pre v-else-if="runError" class="text-[11px] font-mono whitespace-pre-wrap" style="color: #d70015">{{ runError }}</pre>
              <div v-else class="text-[11px] text-muted">等待运行结果</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 配置面板 -->
      <aside class="w-[320px] shrink-0 bg-white border-l border-line">
        <NodeConfigPanel
          v-if="selectedNode"
          :node-id="selectedNode.id"
          :node-type="selectedNode.type as string"
          :data="selectedNode.data"
          :upstream-vars="upstreamVars"
          :models="models"
          :datasets="datasets"
          @update="updateNodeData"
        />
        <div v-else class="h-full flex flex-col items-center justify-center text-center px-6">
          <div class="w-10 h-10 rounded-xl bg-[rgba(118,118,128,0.08)] text-[rgba(60,60,67,0.38)] flex items-center justify-center mb-2">
            <LaIcon name="sliders" :size="18" />
          </div>
          <div class="text-[12.5px] text-muted">选择画布上的节点<br />在这里配置参数</div>
        </div>
      </aside>
    </div>

    <!-- 运行输入 -->
    <NModal v-model:show="showInputs" preset="card" title="运行工作流" class="!w-[480px]" :bordered="false">
      <div class="space-y-3">
        <div v-for="p in startParams" :key="p.name">
          <div class="text-[12.5px] text-muted mb-1">
            {{ p.name }}
            <span class="text-[11px]">（{{ p.type }}{{ p.required ? '，必填' : '' }}）</span>
            <span v-if="p.description" class="text-[11px] text-muted">· {{ p.description }}</span>
          </div>
          <NInput v-model:value="runInputs[p.name]" :placeholder="String(p.default ?? '')" />
        </div>
        <div v-if="!startParams.length" class="text-[12.5px] text-muted">
          开始节点未定义输入参数，将直接运行。
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="showInputs = false">取消</NButton>
          <NButton size="small" type="primary" @click="startRun">开始运行</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
