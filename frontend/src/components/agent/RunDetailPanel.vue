<script setup lang="ts">
import { computed } from 'vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { formatDuration } from '@/utils/format'

export interface RunSnapshot {
  runId?: string
  status: 'idle' | 'running' | 'succeeded' | 'failed'
  model?: string
  mode?: string
  usage?: Record<string, number>
  durationMs?: number
  toolCalls?: { name: string; arguments: Record<string, any>; output?: any; error?: string; durationMs?: number }[]
  knowledge?: { document_name: string; score: number; content: string }[]
  error?: string
}

const props = defineProps<{ run: RunSnapshot | null; config: Record<string, any> }>()

const statusText = computed(() => {
  switch (props.run?.status) {
    case 'running':
      return '执行中'
    case 'succeeded':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return '待运行'
  }
})

const statusStyle = computed(() => {
  switch (props.run?.status) {
    case 'running':
      return 'background:rgba(0,122,255,0.12);color:#007AFF'
    case 'succeeded':
      return 'background:rgba(52,199,89,0.14);color:#248A3D'
    case 'failed':
      return 'background:rgba(255,59,48,0.12);color:#D70015'
    default:
      return 'background:rgba(118,118,128,0.10);color:#8E8E93'
  }
})
</script>

<template>
  <div class="h-full flex flex-col min-h-0 bg-white">
    <div class="h-[52px] shrink-0 px-4 flex items-center justify-between border-b border-line">
      <span class="text-[14px] font-semibold text-ink tracking-tight">运行详情</span>
      <span class="la-pill" :style="statusStyle">
        <span
          v-if="run?.status === 'running'"
          class="w-[5px] h-[5px] rounded-full"
          style="background: currentColor; animation: la-pulse-dot 1.2s ease-in-out infinite"
        ></span>
        {{ statusText }}
      </span>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4 text-[12px]">
      <!-- 指标 -->
      <div class="grid grid-cols-2 gap-2">
        <div class="rounded-[12px] p-2.5" style="background: rgba(118, 118, 128, 0.07)">
          <div class="text-[11px] text-muted">模型</div>
          <div class="text-[12.5px] text-ink truncate mt-0.5 font-medium">
            {{ run?.model || config.model_name || '—' }}
          </div>
        </div>
        <div class="rounded-[12px] p-2.5" style="background: rgba(118, 118, 128, 0.07)">
          <div class="text-[11px] text-muted">执行模式</div>
          <div class="text-[12.5px] text-ink mt-0.5 font-medium">
            {{ (run?.mode || config.mode) === 'react' ? 'ReAct' : 'Function Calling' }}
          </div>
        </div>
        <div class="rounded-[12px] p-2.5" style="background: rgba(118, 118, 128, 0.07)">
          <div class="text-[11px] text-muted">耗时</div>
          <div class="text-[12.5px] text-ink mt-0.5 font-medium tabular-nums">
            {{ formatDuration(run?.durationMs) }}
          </div>
        </div>
        <div class="rounded-[12px] p-2.5" style="background: rgba(118, 118, 128, 0.07)">
          <div class="text-[11px] text-muted">Token</div>
          <div class="text-[12.5px] text-ink mt-0.5 font-medium tabular-nums">
            {{ run?.usage?.total_tokens || 0 }}
            <span class="text-[10.5px] text-muted font-normal">
              ({{ run?.usage?.prompt_tokens || 0 }} / {{ run?.usage?.completion_tokens || 0 }})
            </span>
          </div>
        </div>
      </div>

      <!-- 知识召回 -->
      <div>
        <div class="flex items-center gap-1.5 text-[12px] font-semibold text-ink mb-1.5">
          <LaIcon name="book" :size="13" /> 知识召回
          <span class="text-[11px] text-muted font-normal">({{ run?.knowledge?.length || 0 }})</span>
        </div>
        <div v-if="run?.knowledge?.length" class="space-y-1.5">
          <details
            v-for="(k, i) in run.knowledge"
            :key="i"
            class="rounded-[10px] px-2.5 py-2"
            style="background: rgba(118, 118, 128, 0.07)"
          >
            <summary class="cursor-pointer text-[11.5px] text-[rgba(60,60,67,0.72)]">
              [{{ i + 1 }}] {{ k.document_name }} · {{ k.score.toFixed(3) }}
            </summary>
            <div class="text-[11px] text-muted mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">
              {{ k.content }}
            </div>
          </details>
        </div>
        <div
          v-else
          class="text-[11.5px] text-muted rounded-[10px] px-2.5 py-2.5"
          style="background: rgba(118, 118, 128, 0.06)"
        >
          本次未召回知识片段
        </div>
      </div>

      <!-- 工具调用 -->
      <div>
        <div class="flex items-center gap-1.5 text-[12px] font-semibold text-ink mb-1.5">
          <LaIcon name="tool" :size="13" /> 工具调用
          <span class="text-[11px] text-muted font-normal">({{ run?.toolCalls?.length || 0 }})</span>
        </div>
        <div v-if="run?.toolCalls?.length" class="space-y-1.5">
          <div
            v-for="(t, i) in run.toolCalls"
            :key="i"
            class="rounded-[10px] p-2.5"
            style="background: rgba(118, 118, 128, 0.07)"
          >
            <div class="flex items-center justify-between">
              <span class="text-[11.5px] font-semibold text-ink">{{ t.name }}</span>
              <span
                class="text-[10.5px] font-medium"
                :style="t.error ? 'color:#D70015' : 'color:#248A3D'"
              >
                {{ t.error ? '失败' : `成功 · ${t.durationMs || 0}ms` }}
              </span>
            </div>
            <div class="text-[10.5px] text-muted mt-1 break-all">
              <span class="text-[#8E8E93]">入参：</span>{{ JSON.stringify(t.arguments) }}
            </div>
            <div v-if="t.error" class="text-[10.5px] mt-1" style="color: #d70015">{{ t.error }}</div>
            <div
              v-else
              class="text-[10.5px] text-[rgba(60,60,67,0.7)] mt-1 max-h-28 overflow-y-auto whitespace-pre-wrap break-all"
            >
              <span class="text-[#8E8E93]">结果：</span>{{ JSON.stringify(t.output).slice(0, 600) }}
            </div>
          </div>
        </div>
        <div
          v-else
          class="text-[11.5px] text-muted rounded-[10px] px-2.5 py-2.5"
          style="background: rgba(118, 118, 128, 0.06)"
        >
          本次未调用工具
        </div>
      </div>

      <div
        v-if="run?.error"
        class="rounded-[10px] p-2.5 text-[11.5px]"
        style="background: rgba(255, 59, 48, 0.1); color: #d70015"
      >
        {{ run.error }}
      </div>

      <div v-if="run?.runId" class="text-[10.5px] text-muted font-mono break-all opacity-70">
        run_id: {{ run.runId }}
      </div>
    </div>
  </div>
</template>
