<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string; type?: 'app' | 'doc' | 'run' | 'index' }>()

/** iOS 系统色 + 12% 半透明底，构成胶囊标签 */
const SYS = {
  gray: { fg: '#8E8E93', bg: 'rgba(142,142,147,0.12)' },
  blue: { fg: '#184CFF', bg: 'rgba(24,76,255,0.12)' },
  green: { fg: '#248A3D', bg: 'rgba(52,199,89,0.14)' },
  orange: { fg: '#C86A00', bg: 'rgba(255,149,0,0.14)' },
  red: { fg: '#D70015', bg: 'rgba(255,59,48,0.12)' },
}

const map: Record<string, { text: string; tone: keyof typeof SYS; dot?: boolean }> = {
  draft: { text: '未发布', tone: 'gray' },
  published: { text: '已发布', tone: 'green', dot: true },
  waiting: { text: '等待中', tone: 'gray' },
  parsing: { text: '解析中', tone: 'blue' },
  splitting: { text: '切片中', tone: 'blue' },
  indexing: { text: '索引中', tone: 'orange' },
  completed: { text: '已完成', tone: 'green', dot: true },
  ready: { text: '已就绪', tone: 'green', dot: true },
  empty: { text: '空', tone: 'gray' },
  failed: { text: '失败', tone: 'red' },
  running: { text: '运行中', tone: 'blue', dot: true },
  succeeded: { text: '成功', tone: 'green', dot: true },
  success: { text: '成功', tone: 'green', dot: true },
  canceled: { text: '已取消', tone: 'gray' },
}

const info = computed(() => map[props.status] || { text: props.status, tone: 'gray' as const })
const color = computed(() => SYS[info.value.tone])
</script>

<template>
  <span
    class="la-pill"
    :style="{ color: color.fg, background: color.bg }"
  >
    <span
      v-if="info.dot"
      class="w-[5px] h-[5px] rounded-full"
      :style="{ background: color.fg }"
    ></span>
    {{ info.text }}
  </span>
</template>
