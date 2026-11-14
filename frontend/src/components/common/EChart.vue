<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'

/* 图表统一按 iOS 视觉规范渲染：系统色序列、SF 字体、极淡网格 */
const IOS_FONT =
  '-apple-system, BlinkMacSystemFont, "SF Pro Text", Inter, "PingFang SC", "Microsoft YaHei", sans-serif'

echarts.registerTheme('lightagent-ios', {
  color: ['#007AFF', '#34C759', '#FF9500', '#AF52DE', '#30B0C7', '#5856D6', '#FF3B30', '#8E8E93'],
  backgroundColor: 'transparent',
  textStyle: { fontFamily: IOS_FONT, fontSize: 11, color: 'rgba(60,60,67,0.6)' },
  categoryAxis: {
    axisLine: { lineStyle: { color: 'rgba(60,60,67,0.13)' } },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(60,60,67,0.5)', fontSize: 11 },
    splitLine: { show: false },
  },
  valueAxis: {
    axisLine: { show: false },
    axisTick: { show: false },
    axisLabel: { color: 'rgba(60,60,67,0.5)', fontSize: 11 },
    splitLine: { lineStyle: { color: 'rgba(60,60,67,0.07)' } },
  },
  tooltip: {
    backgroundColor: 'rgba(28,28,30,0.94)',
    borderWidth: 0,
    padding: [7, 10],
    textStyle: { color: '#fff', fontSize: 12, fontFamily: IOS_FONT },
    extraCssText: 'border-radius:10px;box-shadow:0 8px 28px -8px rgba(0,0,0,0.4);',
  },
  legend: {
    textStyle: { color: 'rgba(60,60,67,0.6)', fontSize: 11, fontFamily: IOS_FONT },
    itemWidth: 8,
    itemHeight: 8,
  },
})

const props = withDefaults(
  defineProps<{ option: echarts.EChartsCoreOption; height?: string; loading?: boolean }>(),
  { height: '240px', loading: false },
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
      color: '#007AFF',
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
  chart.value = echarts.init(el.value, 'lightagent-ios')
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
  <div ref="el" :style="{ height, width: '100%' }"></div>
</template>
