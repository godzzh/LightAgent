<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NSpin } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import StatCard from '@/components/common/StatCard.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import VEcharts from '@/components/common/VEcharts/index.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { dashboardApi } from '@/api/auth'
import { formatNumber, truncate, formatDate, formatDuration } from '@/utils/format'

const router = useRouter()

const loading = ref(true)
const error = ref('')
const overview = ref<any>(null)
const recent = ref<any>({ applications: [], runs: [] })
const trend = ref<any>({ trend: [], models: [] })

const stats = computed(() => overview.value?.stats || {})

const trendOption = computed(() => ({
  grid: { left: 4, right: 8, top: 18, bottom: 0, containLabel: true },
  tooltip: { trigger: 'axis', axisPointer: { type: 'line', lineStyle: { color: 'rgba(24,76,255,0.3)' } } },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: (trend.value.trend || []).map((d: any) => d.date.slice(5)),
    axisLine: { lineStyle: { color: 'rgba(60,60,67,0.13)' } },
    axisLabel: { color: 'rgba(60,60,67,0.5)', fontSize: 11 },
    axisTick: { show: false },
  },
  yAxis: {
    type: 'value',
    splitLine: { lineStyle: { color: 'rgba(60,60,67,0.07)' } },
    axisLabel: { color: 'rgba(60,60,67,0.5)', fontSize: 11 },
  },
  series: [
    {
      type: 'line',
      smooth: 0.4,
      symbol: 'circle',
      symbolSize: 6,
      showSymbol: false,
      emphasis: { scale: 1.4 },
      data: (trend.value.trend || []).map((d: any) => d.count),
      itemStyle: { color: '#184CFF', borderColor: '#fff', borderWidth: 2 },
      lineStyle: { width: 2.5, color: '#184CFF', type: 'solid' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24,76,255,0.20)' },
            { offset: 1, color: 'rgba(24,76,255,0.01)' },
          ],
        },
      },
    },
  ],
}))

const modelOption = computed(() => {
  const models = trend.value.models || []
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, icon: 'circle', itemWidth: 7, itemHeight: 7 },
    color: ['#184CFF', '#34C759', '#FF9500', '#AF52DE', '#30B0C7', '#5856D6'],
    series: [
      {
        type: 'pie',
        radius: ['52%', '72%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: true,
        padAngle: 2,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}', fontSize: 11, color: '#59595e' },
        data: models.length
          ? models.map((m: any) => ({ name: m.name, value: m.count }))
          : [{ name: '暂无调用', value: 1, itemStyle: { color: 'rgba(120,120,128,0.18)' } }],
      },
    ],
  }
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [o, r, t] = await Promise.all([
      dashboardApi.overview(),
      dashboardApi.recent(),
      dashboardApi.trend(),
    ])
    overview.value = o
    recent.value = r
    trend.value = t
  } catch (e: any) {
    error.value = e?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const quickActions = [
  {
    label: '创建 Agent',
    desc: '配置提示词与工具',
    icon: 'robot',
    to: '/applications',
    bg: 'linear-gradient(160deg, #6B8CFF 0%, #184CFF 100%)',
  },
  {
    label: '创建工作流',
    desc: '可视化节点编排',
    icon: 'flow',
    to: '/workflows',
    bg: 'linear-gradient(160deg, #7B79E8 0%, #5856D6 100%)',
  },
  {
    label: '创建知识库',
    desc: '上传文档做 RAG',
    icon: 'book',
    to: '/knowledge',
    bg: 'linear-gradient(160deg, #55C8DB 0%, #30B0C7 100%)',
  },
  {
    label: '配置模型',
    desc: '接入 DeepSeek',
    icon: 'cpu',
    to: '/models',
    bg: 'linear-gradient(160deg, #5BD97A 0%, #34C759 100%)',
  },
]

function openRun(run: any) {
  router.push({ name: 'logs', query: { run: run.id } })
}

onMounted(load)
</script>

<template>
  <div class="la-page">
    <PageHeader title="工作空间" subtitle="平台整体运行概览与快速入口">
      <template #actions>
        <NButton :loading="loading" @click="load">
          <template #icon><LaIcon name="refresh" :size="14" /></template>
          刷新
        </NButton>
      </template>
    </PageHeader>

    <!-- 错误态 -->
    <div v-if="error" class="la-card p-10 text-center" role="alert" aria-live="assertive">
      <div class="flex items-center justify-center gap-2 text-[14px]" style="color: var(--la-error-text)">
        <LaIcon name="warn" :size="15" />
        <span>{{ error }}</span>
      </div>
      <NButton class="mt-4" @click="load">重试</NButton>
    </div>

    <template v-else>
      <!-- 统计卡片 -->
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
        <StatCard label="Agent 总数" :value="stats.applications ?? 0" icon="robot" tone="blue" :loading="loading" />
        <StatCard label="已发布应用" :value="stats.published ?? 0" icon="zap" tone="green" :loading="loading" />
        <StatCard label="知识库" :value="stats.datasets ?? 0" icon="book" tone="teal" :loading="loading" />
        <StatCard label="工作流" :value="stats.workflows ?? 0" icon="flow" tone="indigo" :loading="loading" />
        <StatCard label="累计运行" :value="formatNumber(stats.runs)" icon="history" tone="purple" :loading="loading" />
        <StatCard label="Token 消耗" :value="formatNumber(stats.tokens)" icon="chart" tone="orange" :loading="loading" />
      </div>

      <!-- 图表区 -->
      <div class="grid grid-cols-1 xl:grid-cols-3 gap-3 mt-4">
        <div class="la-card p-4 xl:col-span-2">
          <div class="flex items-center justify-between mb-1 px-0.5">
            <div class="text-[14px] font-semibold text-ink tracking-tight">应用调用趋势</div>
            <span class="text-[11.5px] text-muted">近 7 天</span>
          </div>
          <VEcharts :options="trendOption" height="228px" label="近 7 天应用调用趋势折线图" />
        </div>
        <div class="la-card p-4">
          <div class="text-[14px] font-semibold text-ink tracking-tight mb-1 px-0.5">模型使用分布</div>
          <VEcharts :options="modelOption" height="228px" label="模型使用分布饼图" />
        </div>
      </div>

      <!-- 列表区（iOS 分组列表） -->
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-3 mt-4">
        <div class="la-card">
          <div class="flex items-center justify-between px-4 h-[46px]">
            <span class="text-[14px] font-semibold text-ink tracking-tight">最近创建的应用</span>
            <button class="text-[12.5px] text-primary font-medium ios-press" @click="router.push('/applications')">
              全部
            </button>
          </div>
          <div v-if="loading" class="py-10 flex justify-center"><NSpin /></div>
          <EmptyState
            v-else-if="!recent.applications?.length"
            compact
            icon="robot"
            title="还没有应用"
            description="从模板创建一个 Agent，几分钟即可跑通第一次对话"
          >
            <NButton type="primary" @click="router.push('/applications')">创建应用</NButton>
          </EmptyState>
          <div v-else class="la-list border-t border-line">
            <div
              v-for="a in recent.applications"
              :key="a.id"
              class="la-row cursor-pointer"
              @click="a.app_type === 'workflow' ? router.push(`/workflows/${a.id}`) : router.push(`/applications/${a.id}/agent`)"
            >
              <span
                class="la-icon-tile w-8 h-8 shrink-0"
                :style="{
                  background:
                    a.app_type === 'workflow'
                      ? 'linear-gradient(160deg, #7B79E8 0%, #5856D6 100%)'
                      : 'linear-gradient(160deg, #6B8CFF 0%, #184CFF 100%)',
                }"
              >
                <LaIcon :name="a.app_type === 'workflow' ? 'flow' : 'robot'" :size="16" :stroke-width="2" />
              </span>
              <div class="min-w-0 flex-1 ml-3">
                <div class="text-[13.5px] text-ink truncate tracking-tight">{{ a.name }}</div>
                <div class="text-[11.5px] text-muted mt-0.5">{{ formatDate(a.created_at) }}</div>
              </div>
              <StatusTag :status="a.status" />
              <LaIcon name="chevronRight" :size="14" class="text-muted ml-2 opacity-60" />
            </div>
          </div>
        </div>

        <div class="la-card">
          <div class="flex items-center justify-between px-4 h-[46px]">
            <span class="text-[14px] font-semibold text-ink tracking-tight">最近运行记录</span>
            <button class="text-[12.5px] text-primary font-medium ios-press" @click="router.push('/logs')">
              全部
            </button>
          </div>
          <div v-if="loading" class="py-10 flex justify-center"><NSpin /></div>
          <EmptyState
            v-else-if="!recent.runs?.length"
            compact
            icon="history"
            title="暂无运行记录"
            description="在 Agent 调试页发起一次对话，这里会记录耗时与 Token 消耗"
          />
          <div v-else class="la-list border-t border-line">
            <div
              v-for="r in recent.runs"
              :key="r.id"
              class="la-row cursor-pointer"
              @click="openRun(r)"
            >
              <div class="min-w-0 flex-1">
                <div class="text-[13.5px] text-ink truncate tracking-tight">
                  {{ truncate(r.user_input, 40) || '（无输入）' }}
                </div>
                <div class="text-[11.5px] text-muted mt-0.5">
                  {{ r.application_name }} · {{ formatDuration(r.duration_ms) }} · {{ r.total_tokens }} tokens
                </div>
              </div>
              <StatusTag :status="r.status" />
            </div>
          </div>
        </div>
      </div>

      <!-- 快速入口 -->
      <div class="la-section-label mt-6 mb-2">快速开始</div>
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <button
          v-for="q in quickActions"
          :key="q.label"
          class="la-tile p-4"
          @click="router.push(q.to)"
        >
          <span class="la-icon-tile w-10 h-10" :style="{ background: q.bg }">
            <LaIcon :name="q.icon" :size="19" :stroke-width="2" />
          </span>
          <div class="text-[13.5px] font-semibold text-ink mt-3 tracking-tight">{{ q.label }}</div>
          <div class="text-[11.5px] text-muted mt-0.5">{{ q.desc }}</div>
        </button>
      </div>
    </template>
  </div>
</template>
