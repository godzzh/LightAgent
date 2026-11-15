<script setup lang="ts">
/**
 * 统一图标适配层 —— 底层使用 @remixicon/vue 的 Vue 组件（Remix Icon）。
 *
 * 对外保持与旧版一致的 API（name / size / strokeWidth / color / class），
 * 因此全项目上百处 <LaIcon> 调用无需改动即可切换到 Remix Icon。
 *
 * - name 支持：语义别名（'dashboard'、'flow'…）、旧版 kebab/camel 名、
 *   以及直接传 Remix 组件名（'RiRocketLine'）。
 * - 未知名称统一兜底为 RiQuestionLine，避免渲染空白。
 * - 显式静态导入所用图标（而非 import *），让 Rollup 只打包这 53 个组件，
 *   避免把 3200+ 图标全量打进产物。
 * - Remix Icon 为 24x24 网格、线性/面性两套且笔画宽度固定，
 *   统一采用 Line 线性风格（同一层级只保留一种图标风格，保证视觉一致性）；
 *   strokeWidth 保留仅为兼容旧调用签名，不参与渲染。
 */
import { computed, type Component } from 'vue'
import {
  RiAddLine, RiApps2Line, RiArrowDownSLine, RiArrowLeftSLine, RiArrowRightSLine,
  RiBarChartBoxLine, RiBook2Line, RiBracesLine, RiBrainLine, RiCheckLine,
  RiCloseLine, RiCodeLine, RiCpuLine, RiDashboardLine, RiDatabase2Line,
  RiDeleteBinLine, RiDownload2Line, RiEditLine, RiEqualizerLine, RiErrorWarningLine,
  RiExternalLinkLine, RiEyeLine, RiFileCopyLine, RiFileList3Line, RiFilter3Line,
  RiFlagLine, RiFlashlightLine, RiFunctionLine, RiGitBranchLine, RiGlobalLine,
  RiHistoryLine, RiInformationLine, RiKey2Line, RiLightbulbLine, RiLogoutBoxLine,
  RiMagicLine, RiMessage3Line, RiMore2Line, RiNodeTree, RiPlayLine,
  RiQuestionLine, RiRefreshLine, RiRobot2Line, RiRouteLine, RiSearchLine,
  RiSendPlaneLine, RiSettings3Line, RiShieldCheckLine, RiSparkling2Line, RiStackLine, RiStopLine,
  RiTimeLine, RiToolsLine, RiUpload2Line, RiUser3Line,
} from '@remixicon/vue'

/** 组件名 -> 组件（仅收录本适配层实际用到的图标） */
const ICONS: Record<string, Component> = {
  RiAddLine, RiApps2Line, RiArrowDownSLine, RiArrowLeftSLine, RiArrowRightSLine,
  RiBarChartBoxLine, RiBook2Line, RiBracesLine, RiBrainLine, RiCheckLine,
  RiCloseLine, RiCodeLine, RiCpuLine, RiDashboardLine, RiDatabase2Line,
  RiDeleteBinLine, RiDownload2Line, RiEditLine, RiEqualizerLine, RiErrorWarningLine,
  RiExternalLinkLine, RiEyeLine, RiFileCopyLine, RiFileList3Line, RiFilter3Line,
  RiFlagLine, RiFlashlightLine, RiFunctionLine, RiGitBranchLine, RiGlobalLine,
  RiHistoryLine, RiInformationLine, RiKey2Line, RiLightbulbLine, RiLogoutBoxLine,
  RiMagicLine, RiMessage3Line, RiMore2Line, RiNodeTree, RiPlayLine,
  RiQuestionLine, RiRefreshLine, RiRobot2Line, RiRouteLine, RiSearchLine,
  RiSendPlaneLine, RiSettings3Line, RiShieldCheckLine, RiSparkling2Line, RiStackLine, RiStopLine,
  RiTimeLine, RiToolsLine, RiUpload2Line, RiUser3Line,
}

const props = withDefaults(
  defineProps<{ name: string; size?: number | string; strokeWidth?: number; color?: string }>(),
  { size: 16, strokeWidth: 1.8 },
)

/** 语义别名 -> Remix 线性图标组件名 */
const ALIAS: Record<string, string> = {
  // 导航 / 系统
  dashboard: 'RiDashboardLine',
  apps: 'RiApps2Line',
  flow: 'RiNodeTree',
  book: 'RiBook2Line',
  tool: 'RiToolsLine',
  cpu: 'RiCpuLine',
  logs: 'RiFileList3Line',
  settings: 'RiSettings3Line',
  chart: 'RiBarChartBoxLine',
  history: 'RiHistoryLine',
  database: 'RiDatabase2Line',
  globe: 'RiGlobalLine',
  external: 'RiExternalLinkLine',
  key: 'RiKey2Line',
  user: 'RiUser3Line',
  logout: 'RiLogoutBoxLine',
  eye: 'RiEyeLine',
  info: 'RiInformationLine',
  warn: 'RiErrorWarningLine',
  time: 'RiTimeLine',
  clock: 'RiTimeLine',
  zap: 'RiFlashlightLine',
  sliders: 'RiEqualizerLine',
  filter: 'RiFilter3Line',
  sparkles: 'RiSparkling2Line',
  shield: 'RiShieldCheckLine',
  robot: 'RiRobot2Line',
  magic: 'RiMagicLine',
  stack: 'RiStackLine',
  function: 'RiFunctionLine',
  route: 'RiRouteLine',
  brain: 'RiBrainLine',
  lightbulb: 'RiLightbulbLine',

  // 操作
  plus: 'RiAddLine',
  search: 'RiSearchLine',
  trash: 'RiDeleteBinLine',
  edit: 'RiEditLine',
  play: 'RiPlayLine',
  more: 'RiMore2Line',
  check: 'RiCheckLine',
  close: 'RiCloseLine',
  send: 'RiSendPlaneLine',
  stop: 'RiStopLine',
  refresh: 'RiRefreshLine',
  copy: 'RiFileCopyLine',
  upload: 'RiUpload2Line',
  download: 'RiDownload2Line',
  chevronDown: 'RiArrowDownSLine',
  chevronRight: 'RiArrowRightSLine',
  chevronLeft: 'RiArrowLeftSLine',

  // 工作流节点（后端 NODE_DEFINITIONS 的 icon 值）
  code: 'RiCodeLine',
  'git-branch': 'RiGitBranchLine',
  variable: 'RiBracesLine',
  message: 'RiMessage3Line',
  flag: 'RiFlagLine',
}

/** 小写化便于容错匹配（去掉非字母数字） */
const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, '')
const NORMALIZED_ALIAS: Record<string, string> = Object.fromEntries(
  Object.entries(ALIAS).map(([k, v]) => [norm(k), v]),
)

const iconComponent = computed<Component>(() => {
  const raw = (props.name || '').trim()

  // 1) 直接传 Remix 组件名（优先，方便后续扩展未收录的图标）
  if (ICONS[raw]) return ICONS[raw]

  // 2) 语义别名（含 camelCase / kebab-case 容错），未知名称兜底
  return ICONS[NORMALIZED_ALIAS[norm(raw)] || 'RiQuestionLine'] || ICONS.RiQuestionLine
})

const px = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <component
    :is="iconComponent"
    :size="px"
    :color="color || 'currentColor'"
    class="inline-block shrink-0 align-[-0.125em]"
    aria-hidden="true"
  />
</template>
