<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import LaIcon from '@/components/common/LaIcon.vue'

const props = defineProps<{
  id: string
  data: Record<string, any>
  selected?: boolean
  type: string
}>()

const status = computed(() => props.data.__status as string | undefined)
const color = computed(() => props.data.__color || '#007AFF')
const label = computed(() => props.data.title || props.data.__label || props.type)

/** 节点外环：执行状态优先，其次选中态 */
const ringStyle = computed(() => {
  switch (status.value) {
    case 'running':
      return 'box-shadow:0 0 0 3px rgba(0,122,255,0.25), 0 8px 24px -10px rgba(0,122,255,0.45)'
    case 'succeeded':
      return 'box-shadow:0 0 0 3px rgba(52,199,89,0.22), 0 6px 18px -10px rgba(0,0,0,0.2)'
    case 'failed':
      return 'box-shadow:0 0 0 3px rgba(255,59,48,0.22), 0 6px 18px -10px rgba(0,0,0,0.2)'
    default:
      return props.selected
        ? 'box-shadow:0 0 0 3px rgba(0,122,255,0.18), 0 8px 22px -12px rgba(0,0,0,0.24)'
        : 'box-shadow:0 1px 2px rgba(0,0,0,0.05), 0 6px 16px -12px rgba(0,0,0,0.16)'
  }
})

const hasInput = computed(() => props.type !== 'start')
const isBranch = computed(() => props.type === 'condition')
</script>

<template>
  <div
    class="bg-white min-w-[184px] max-w-[224px] transition-all duration-200"
    :style="`border-radius:14px;border:0.5px solid rgba(60,60,67,0.13);${ringStyle}`"
  >
    <Handle v-if="hasInput" type="target" :position="Position.Left" />

    <div class="flex items-center gap-2 px-3 h-[38px]">
      <span
        class="w-[22px] h-[22px] rounded-[7px] flex items-center justify-center text-white shrink-0"
        :style="{
          background: color,
          boxShadow: 'inset 0 0.5px 0 rgba(255,255,255,0.3), 0 1px 2px rgba(0,0,0,0.14)',
        }"
      >
        <LaIcon :name="data.__icon || 'zap'" :size="12" :stroke-width="2" />
      </span>
      <span class="text-[12.5px] font-semibold text-ink truncate flex-1 tracking-tight">{{ label }}</span>
      <span
        v-if="status === 'running'"
        class="w-[7px] h-[7px] rounded-full"
        style="background: #007aff; animation: la-pulse-dot 1.1s ease-in-out infinite"
      ></span>
      <LaIcon v-else-if="status === 'succeeded'" name="check" :size="12" style="color: #248a3d" />
      <LaIcon v-else-if="status === 'failed'" name="close" :size="12" style="color: #ff3b30" />
    </div>

    <div class="px-3 pb-2 -mt-0.5 text-[11px] text-muted truncate">
      {{ data.__desc || data.__typeLabel || type }}
    </div>

    <!-- 条件节点双出口 -->
    <template v-if="isBranch">
      <div class="flex justify-between px-3 pb-1.5 text-[10px] text-muted">
        <span>是</span><span>否</span>
      </div>
      <Handle id="true" type="source" :position="Position.Right" :style="{ top: '58%' }" />
      <Handle id="false" type="source" :position="Position.Right" :style="{ top: '80%' }" />
    </template>
    <Handle v-else-if="type !== 'end' && type !== 'answer'" type="source" :position="Position.Right" />
  </div>
</template>
