<template>
  <div
    ref="el"
    class="vecharts w-full min-w-0"
    :style="{ height: props.height || '100%' }"
    role="img"
    :aria-label="label || '数据图表'"
    @mouseleave="dismissTooltip"
    @pointercancel="dismissTooltip"
    @click="dismissTooltip"
  ></div>
</template>
<script setup lang="ts">
import { shallowRef, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart, LineChart, PieChart, ScatterChart } from 'echarts/charts'
import {
  GridComponent, TooltipComponent, LegendComponent, LegendScrollComponent,
  TitleComponent, DatasetComponent, TransformComponent, MarkLineComponent,
  GraphicComponent, DataZoomComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsCoreOption, EChartsType } from 'echarts/core'
import { useElementSize } from '@vueuse/core'

echarts.use([
  BarChart, LineChart, PieChart, ScatterChart,
  GridComponent, TooltipComponent, LegendComponent, LegendScrollComponent,
  TitleComponent, DatasetComponent, TransformComponent, MarkLineComponent,
  GraphicComponent, DataZoomComponent, CanvasRenderer,
])

const props = withDefaults(defineProps<{
  options?: Record<string, any>
  autoPlay?: boolean
  dismissTooltipOnLeave?: boolean
  /** 无障碍标签 */
  label?: string
  /** 容器高度，默认 100%（父级需有确定高度） */
  height?: string
}>(), { options: () => ({}), autoPlay: false, dismissTooltipOnLeave: false, label: '', height: '100%' })

const emit = defineEmits<{
  (e: 'itemClick', params: unknown): void
  (e: 'legendSelectChanged', params: unknown): void
  (e: 'chartMouseover', params: unknown): void
  (e: 'rendered'): void
}>()

const el = ref<HTMLDivElement | null>(null)
const myChart = shallowRef<EChartsType | null>(null)
// 注意：解构必须重命名为 boxWidth/boxHeight，避免与 props.height 同名遮蔽，
// 否则 :style 里的 height 会错误地引用到 ResizeObserver 测量值。
const { width: boxWidth, height: boxHeight } = useElementSize(el)

const dismissTooltip = () => {
  if (!props.dismissTooltipOnLeave) return
  myChart.value?.dispatchAction({ type: 'hideTip' })
}

let playTimer: ReturnType<typeof setInterval> | null = null
let currentIndex = 0
let optionsApplied = false

const measureBox = () => {
  const target = el.value
  if (!target) return null
  const boxWidth = target.clientWidth
  const boxHeight = target.clientHeight
  if (boxWidth <= 0 || boxHeight <= 0) return null
  return { width: boxWidth, height: boxHeight }
}

const setOptions = () => {
  const options = props.options || {}
  myChart.value?.setOption({
    color: ['#184CFF', '#34C759', '#FF9500', '#AF52DE', '#30B0C7', '#5856D6', '#FF3B30', '#8E8E93'],
    textStyle: { fontFamily: '-apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif' },
    ...options,
    tooltip: {
      className: 'vecharts-tooltip',
      extraCssText: 'border-radius:6px;box-shadow:0 8px 28px -8px rgba(0,0,0,0.4);',
      ...(options.tooltip || {}),
    },
    grid: { top: '20px', left: '10px', containLabel: true, bottom: '10px', right: '10px', ...(options.grid || {}) },
  } as EChartsCoreOption)
  emit('rendered')
}

const stopPlay = () => { if (playTimer) { clearInterval(playTimer); playTimer = null } }

const autoPlaySelect = () => {
  const chart = myChart.value
  const series = props.options?.series
  if (!chart || !Array.isArray(series)) return
  const dataLen = (series[0]?.data as unknown[] | undefined)?.length ?? 0
  if (!dataLen) return
  chart.dispatchAction({ type: 'downplay', seriesIndex: 0, dataIndex: currentIndex })
  currentIndex = (currentIndex + 1) % dataLen
  chart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: currentIndex })
  chart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: currentIndex })
}

/** 容器量出尺寸后才喂首份配置，避免入场动画在 0x0 画布上播放 */
const applyOptions = () => {
  if (!myChart.value || optionsApplied || !measureBox()) return
  optionsApplied = true
  setOptions()
}

/** 仅当尺寸真的变了才 resize：resize() 会掐断正在播放的入场动画 */
const syncSize = () => {
  const chart = myChart.value
  const box = measureBox()
  if (!chart || !box) return
  if (Math.abs(chart.getWidth() - box.width) >= 1 || Math.abs(chart.getHeight() - box.height) >= 1) chart.resize()
  applyOptions()
}

watch(() => props.options, () => {
  myChart.value?.clear()
  currentIndex = 0
  optionsApplied = false
  nextTick(() => applyOptions())
}, { deep: true })
watch([boxWidth, boxHeight], syncSize)

onMounted(() => {
  if (!el.value) return
  const chart = echarts.init(el.value)
  myChart.value = chart
  chart.on('click', (params) => emit('itemClick', params))
  chart.on('legendselectchanged', (params) => emit('legendSelectChanged', params))
  chart.on('mouseover', (params) => emit('chartMouseover', params))
  chart.getZr().on('globalout', dismissTooltip)
  window.addEventListener('blur', dismissTooltip)
  nextTick(() => applyOptions())

  if (!props.autoPlay) return
  chart.on('mouseover', () => {
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0, dataIndex: currentIndex })
    stopPlay()
  })
  chart.on('mouseout', () => { stopPlay(); playTimer = setInterval(autoPlaySelect, 4000) })
  playTimer = setInterval(autoPlaySelect, 4000)
})

onBeforeUnmount(() => {
  window.removeEventListener('blur', dismissTooltip)
  stopPlay()
  myChart.value?.dispose()
  myChart.value = null
})

defineExpose({ chart: myChart })
</script>
<style>
.vecharts-tooltip:empty:not([style]) { display: none; }
</style>
