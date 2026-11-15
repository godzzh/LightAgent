<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'

/* 图表统一按品牌规范渲染：品牌色序列、系统字体、极淡网格。
   文字颜色统一 #59595e / #6e6e73（白底对比度 ≥4.5:1，符合 WCAG AA）。 */
const UI_FONT =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, "PingFang SC", "Microsoft YaHei", sans-serif'

echarts.registerTheme('lightagent', {
  color: ['#184CFF', '#34C759', '#FF9500', '#AF52DE', '#30B0C7', '#5856D6', '#FF3B30', '#8E8E93'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: UI_FONT, fontSize: 11, color: '#59595e' },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(60,60,67,0.13)' } },
    axisTick: { show: false },
    axisLabel: { color: '#6e6e73', fontSize: 11 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: '#6e6e73', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(60,60,67,0.07)' } },
  },
  tooltip: {
    backgroundColor: 'rgba(28,28,30,0.94)',
    borderWidth: 0,
    padding: [7, 10],
    textStyle: { color: '#fff', fontSize: 12, fontFamily: UI_FONT },
    extraCssText: 'border-radius:6px;box-shadow:0 8px 28px -8px rgba(0,0,0,0.4);',
  },
  legend: {
    textStyle: { color: '#59595e', fontSize: 11, fontFamily: UI_FONT },
    itemWidth: 8,
    itemHeight: 8,
  },
})

const props = withDefaults(
  defineProps<{ option: echarts.EChartsCoreOption; height?: string; loading?: boolean; label?: string }>(),
  { height: '240px', loading: false, label: '' },
)

const el = ref<HTMLDivElement | null>(null)
const chart = shallowRef<echarts.ECharts | null>(null)
let observer: ResizeObserver | null = null

function render() {
  if (!chart.value || !props.option) return
  chart.value.setOption(props.option, true)
}

function setLoading(v: boolean) {
  if (!chart.value) return
  if (v) {
    chart.value.showLoading('default', {
      text: '',
      color: '#184CFF',
      maskColor: 'rgba(255,255,255,0.7)',
      spinnerRadius: 9,
      lineWidth: 2,
    })
  } else {
    chart.value.hideLoading()
  }
}

onMounted(() => {
  if (!el.value) return
  chart.value = echarts.init(el.value, 'lightagent')
  render()
  if (props.loading) setLoading(true)
  observer = new ResizeObserver(() => chart.value?.resize())
  observer.observe(el.value)
})

watch(() => props.option, render, { deep: true })
watch(() => props.loading, setLoading)

onBeforeUnmount(() => {
  observer?.disconnect()
  chart.value?.dispose()
})
</script>

<template>
  <div
    ref="el"
    role="img"
    :aria-label="label || '数据图表'"
    :style="{ height, width: '100%' }"
  ></div>
</template>
