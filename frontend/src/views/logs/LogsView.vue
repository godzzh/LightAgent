<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NInput,
  NSelect,
  NSpin,
  NTabPane,
  NTabs,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { logApi } from '@/api/auth'
import { agentApi } from '@/api/agent'
import { workflowApi } from '@/api/workflows'
import type { RunLog } from '@/types'
import { formatDate, formatDuration, formatNumber, truncate } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const message = useMessage()

const tab = ref<'agent' | 'workflow' | 'llm'>('agent')
const loading = ref(false)
const rows = ref<RunLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')
const status = ref<string | null>(null)
const days = ref(7)
const stats = ref<any>(null)

const showDetail = ref(false)
const detail = ref<any>(null)
const detailLoading = ref(false)
const detailType = ref<'agent' | 'workflow'>('agent')

const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '成功', value: 'succeeded' },
  { label: '运行中', value: 'running' },
  { label: '失败', value: 'failed' },
]

async function load() {
  loading.value = true
  try {
    const res = await logApi.runs({
      run_type: tab.value,
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value,
      status: status.value || undefined,
      days: days.value,
      app_id: (route.query.app as string) || undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  stats.value = await logApi.stats(days.value)
}

async function openDetail(row: RunLog) {
  showDetail.value = true
  detailLoading.value = true
  detail.value = null
  detailType.value = row.type === 'workflow' ? 'workflow' : 'agent'
  try {
    detail.value = row.type === 'workflow' ? await workflowApi.runDetail(row.id) : await agentApi.runDetail(row.id)
  } catch {
    message.error('加载运行详情失败')
  } finally {
    detailLoading.value = false
  }
}

const columns = computed<DataTableColumns<RunLog>>(() => [
  {
    title: '状态',
    key: 'status',
    width: 82,
    render: (row) => h(StatusTag, { status: row.status }),
  },
  {
    title: '应用 / 工作流',
    key: 'app_name',
    width: 150,
    render: (row) => h('span', { class: 'text-[12.5px] text-ink' }, row.app_name || '—'),
  },
  {
    title: '输入 / 输出',
    key: 'user_input',
    minWidth: 280,
    render: (row) =>
      h('div', { class: 'min-w-0' }, [
        h('div', { class: 'text-[12.5px] text-ink truncate' }, truncate(row.user_input, 60) || '—'),
        h('div', { class: 'text-[11px] text-muted truncate' }, truncate(row.output, 70) || '—'),
      ]),
  },
  {
    title: '模型',
    key: 'model_name',
    width: 130,
    render: (row) => h('span', { class: 'text-[11.5px] text-[rgba(60,60,67,0.7)]' }, row.model_name || '—'),
  },
  {
    title: 'Token',
    key: 'total_tokens',
    width: 90,
    render: (row) => h('span', { class: 'text-[11.5px] tabular-nums' }, String(row.total_tokens || 0)),
  },
  {
    title: '耗时',
    key: 'duration_ms',
    width: 88,
    render: (row) => h('span', { class: 'text-[11.5px] text-muted' }, formatDuration(row.duration_ms)),
  },
  {
    title: '时间',
    key: 'created_at',
    width: 140,
    render: (row) => h('span', { class: 'text-[11.5px] text-muted' }, formatDate(row.created_at)),
  },
  {
    title: '',
    key: 'action',
    width: 60,
    // LLM 调用日志没有对应的运行轨迹详情接口，不展示按钮，避免点了必然报错
    render: (row) =>
      row.type === 'llm'
        ? null
        : h(
            NButton,
            { quaternary: true, onClick: () => openDetail(row) },
            { default: () => '详情' },
          ),
  },
])

function changeTab(v: string) {
  tab.value = v as any
  page.value = 1
  load()
}

onMounted(async () => {
  await Promise.all([load(), loadStats()])
})
</script>

<template>
  <div class="la-page">
    <PageHeader title="运行日志" subtitle="Agent / Workflow / LLM 调用全链路记录">
      <template #actions>
        <NButton :loading="loading" @click="(() => { load(); loadStats() })()">
          <template #icon><LaIcon name="refresh" :size="14" /></template>
          刷新
        </NButton>
      </template>
    </PageHeader>

    <div v-if="stats" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
      <StatCard label="LLM 调用次数" :value="formatNumber(stats.calls)" icon="zap" />
      <StatCard label="Prompt Tokens" :value="formatNumber(stats.prompt_tokens)" icon="message" />
      <StatCard label="Completion Tokens" :value="formatNumber(stats.completion_tokens)" icon="chart" />
      <StatCard label="平均耗时" :value="formatDuration(stats.avg_latency_ms)" icon="clock" />
    </div>

    <div class="la-card">
      <NTabs :value="tab" type="line" class="px-3 pt-1" @update:value="changeTab">
        <NTabPane name="agent" tab="Agent 运行" />
        <NTabPane name="workflow" tab="Workflow 运行" />
        <NTabPane name="llm" tab="LLM 调用" />
      </NTabs>

      <div class="flex flex-wrap items-center gap-2 px-3 py-2.5 border-b border-line">
        <NInput
          v-model:value="keyword"
          placeholder="搜索输入或输出内容"
          class="la-search !w-[240px]"
          clearable
          @keyup.enter="((page = 1), load())"
          @clear="((page = 1), load())"
        >
          <template #prefix><LaIcon name="search" :size="14" class="text-[rgba(60,60,67,0.38)]" /></template>
        </NInput>
        <NSelect
          :value="status || ''"
          :options="statusOptions"
          class="!w-[130px]"
          @update:value="(v: string) => { status = v || null; page = 1; load() }"
        />
        <NSelect
          :value="days"
          :options="[{ label: '近 1 天', value: 1 }, { label: '近 7 天', value: 7 }, { label: '近 30 天', value: 30 }]"
          class="!w-[120px]"
          @update:value="(v: number) => { days = v; page = 1; load(); loadStats() }"
        />
        <NButton @click="((page = 1), load())">查询</NButton>
        <div class="flex-1"></div>
        <span v-if="route.query.app" class="text-[11.5px] text-muted">
          已按应用过滤
          <button class="text-primary hover:underline ml-1" @click="router.replace({ path: '/logs' })">清除</button>
        </span>
      </div>

      <NDataTable
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: RunLog) => r.id"
        :bordered="false"
        :single-line="false"
        :pagination="{
          page,
          pageSize,
          itemCount: total,
          pageSizes: [20, 50, 100],
          showSizePicker: true,
          onUpdatePage: (p: number) => { page = p; load() },
          onUpdatePageSize: (s: number) => { pageSize = s; page = 1; load() },
        }"
      />
    </div>

    <!-- 详情抽屉 -->
    <NDrawer v-model:show="showDetail" :width="640" placement="right">
      <NDrawerContent title="运行详情" closable>
        <div v-if="detailLoading" class="py-10 flex justify-center"><NSpin /></div>
        <div v-else-if="detail" class="space-y-3">
          <div v-if="detailType === 'agent'">
            <div class="grid grid-cols-2 gap-2 text-[12px]">
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">状态</div>
                <div class="mt-1"><StatusTag :status="detail.run.status" /></div>
              </div>
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">模型 / 模式</div>
                <div class="text-ink mt-1">{{ detail.run.model_name }} · {{ detail.run.mode }}</div>
              </div>
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">Token</div>
                <div class="text-ink mt-1">
                  {{ detail.run.total_tokens }}
                  <span class="text-muted text-[10.5px]">
                    ({{ detail.run.prompt_tokens }}/{{ detail.run.completion_tokens }})
                  </span>
                </div>
              </div>
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">耗时 / 步数</div>
                <div class="text-ink mt-1">
                  {{ formatDuration(detail.run.duration_ms) }} · {{ detail.run.steps_count }} 步
                </div>
              </div>
            </div>

            <div class="mt-3">
              <div class="text-[12px] font-medium text-ink mb-1">用户输入</div>
              <div class="bg-[#F7F7F9] border border-line rounded-[8px] p-2 text-[12px] whitespace-pre-wrap">
                {{ detail.run.user_input || '—' }}
              </div>
            </div>
            <div class="mt-2">
              <div class="text-[12px] font-medium text-ink mb-1">最终输出</div>
              <div class="bg-white border border-line rounded-[8px] p-2 text-[12px] whitespace-pre-wrap">
                {{ detail.run.output || '—' }}
              </div>
            </div>

            <div v-if="detail.steps?.length" class="mt-3">
              <div class="text-[12px] font-medium text-ink mb-1">执行轨迹</div>
              <div class="space-y-1.5">
                <div v-for="s in detail.steps" :key="s.id" class="border border-line rounded-[8px] p-2">
                  <div class="flex items-center gap-2 text-[11px]">
                    <span class="px-1.5 py-0.5 rounded bg-[rgba(118,118,128,0.08)] text-[rgba(60,60,67,0.7)]">{{ s.step_type }}</span>
                    <span v-if="s.tool_name" class="text-[#184CFF] font-mono">{{ s.tool_name }}</span>
                    <span class="text-muted">{{ s.duration_ms }}ms</span>
                  </div>
                  <div class="text-[11.5px] text-[rgba(60,60,67,0.7)] mt-1 whitespace-pre-wrap break-all max-h-40 overflow-y-auto">
                    {{ s.content }}
                  </div>
                </div>
              </div>
            </div>
            <div v-if="detail.run.error" role="alert" aria-live="polite" class="mt-2 text-[12px] rounded-[6px] p-2" style="color: var(--la-error-text); background: var(--la-error-bg); border: 1px solid var(--la-error-border)">
              {{ detail.run.error }}
            </div>
          </div>

          <div v-else>
            <div class="grid grid-cols-2 gap-2 text-[12px]">
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">状态</div>
                <div class="mt-1"><StatusTag :status="detail.run.status" /></div>
              </div>
              <div class="border border-line rounded-[8px] p-2">
                <div class="text-[11px] text-muted">耗时</div>
                <div class="text-ink mt-1">{{ formatDuration(detail.run.duration_ms) }}</div>
              </div>
            </div>
            <div class="mt-3">
              <div class="text-[12px] font-medium text-ink mb-1">输入</div>
              <pre class="bg-[#F7F7F9] border border-line rounded-[8px] p-2 text-[11.5px] overflow-x-auto">{{ JSON.stringify(detail.run.inputs, null, 2) }}</pre>
            </div>
            <div class="mt-2">
              <div class="text-[12px] font-medium text-ink mb-1">输出</div>
              <pre class="bg-white border border-line rounded-[8px] p-2 text-[11.5px] overflow-x-auto">{{ JSON.stringify(detail.run.outputs, null, 2) }}</pre>
            </div>
            <div class="mt-3">
              <div class="text-[12px] font-medium text-ink mb-1">节点轨迹</div>
              <div class="space-y-1.5">
                <div v-for="n in detail.nodes" :key="n.node_id" class="border border-line rounded-[8px] p-2">
                  <div class="flex items-center justify-between text-[11.5px]">
                    <span class="text-ink">{{ n.title }} <span class="text-muted font-mono">{{ n.node_id }}</span></span>
                    <StatusTag :status="n.status" />
                  </div>
                  <div class="text-[11px] text-muted mt-1">{{ formatDuration(n.duration_ms) }}</div>
                  <pre v-if="n.error" class="text-[11px] text-[#FF3B30] mt-1 whitespace-pre-wrap">{{ n.error }}</pre>
                  <pre v-else class="text-[11px] text-[rgba(60,60,67,0.7)] mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">{{ JSON.stringify(n.outputs, null, 2) }}</pre>
                </div>
              </div>
            </div>
            <div v-if="detail.run.error" role="alert" aria-live="polite" class="mt-2 text-[12px] rounded-[6px] p-2" style="color: var(--la-error-text); background: var(--la-error-bg); border: 1px solid var(--la-error-border)">
              {{ detail.run.error }}
            </div>
          </div>
        </div>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
