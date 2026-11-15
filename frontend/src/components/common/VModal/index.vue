<template>
  <NModal
    :show="show"
    v-bind="$attrs"
    :auto-focus="false"
    :mask-closable="!loading"
    @esc="onClose"
    @update:show="onUpdateShow"
  >
    <div
      class="v-modal"
      :style="{ width: typeof width === 'number' ? width + 'px' : width }"
      role="dialog"
      aria-modal="true"
      :aria-label="title || '弹窗'"
    >
      <div class="v-modal__title" v-drag>
        <div class="v-modal__title-tt">
          <span class="v-modal__title-name">{{ title }}</span>
          <span v-if="subtitle" class="v-modal__title-sub">{{ subtitle }}</span>
        </div>
        <button
          class="v-modal__close"
          type="button"
          title="关闭"
          aria-label="关闭弹窗"
          :disabled="loading"
          @click="onClose"
        >
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true"><path d="m5 5 10 10M15 5 5 15" /></svg>
        </button>
      </div>
      <div class="v-modal__content" v-loading="loading">
        <NScrollbar style="max-height: calc(100vh - 316px)">
          <div class="v-modal__body"><slot /></div>
        </NScrollbar>
        <div v-if="$slots.footer" class="v-modal__footer"><slot name="footer" /></div>
      </div>
    </div>
  </NModal>
</template>
<script setup lang="ts">
import { NModal, NScrollbar } from 'naive-ui'

const emits = defineEmits<{
  'update:show': [value: boolean]
  close: []
}>()
const props = withDefaults(defineProps<{
  show?: boolean
  title?: string
  /** 可选说明行，显示在主标题右侧 */
  subtitle?: string
  loading?: boolean
  /** 弹窗宽度，默认 520px；可传 number 或 CSS 宽度字符串 */
  width?: number | string
}>(), { show: false, title: '', subtitle: '', loading: false, width: 520 })

function onClose() {
  if (props.loading) return
  emits('close')
  emits('update:show', false)
}
function onUpdateShow(v: boolean) {
  if (!v) onClose()
}
</script>
<style scoped>
.v-modal {
  min-width: 360px;
  max-width: calc(100vw - 32px);
  overflow: visible;
  background: var(--la-bg-elevated, #fff);
  border: 1px solid var(--la-separator, #e5eaf3);
  /* NModal 会把 .n-modal 类挂到本根节点，而 naive-ui 全局覆盖里
     .n-modal { border-radius: 4px !important } 会压掉面板圆角；
     这里用同等 !important + 更具体的 scoped 选择器保证自定义面板为 8px。 */
  border-radius: var(--la-r-panel, 8px) !important;
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.18);
}
.v-modal__title {
  position: relative;
  display: flex;
  height: 56px;
  padding: 0 14px 0 16px;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  background: linear-gradient(90deg, rgba(var(--la-primary-rgb, 24, 76, 255), 0.04), transparent 34%);
  border-bottom: 1px solid var(--la-separator, #e5eaf3);
}
.v-modal__title::before {
  position: absolute; top: 0; left: 0; width: 108px; height: 2px;
  border-radius: 8px 0 0 0;
  background: linear-gradient(90deg, var(--la-blue, #184cff), var(--la-primary-hover, #4770ff), transparent);
  content: '';
}
.v-modal__title-tt { display: flex; min-width: 0; align-items: baseline; gap: 10px; }
.v-modal__title-name { overflow: hidden; color: var(--la-text, #1f2329); font-size: 15px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.v-modal__title-sub { overflow: hidden; color: var(--la-text-3, #86909c); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.v-modal__close {
  display: grid; width: 32px; height: 32px; flex: 0 0 auto; padding: 0; margin-left: auto;
  color: var(--la-text-3, #86909c); background: transparent; border: 0; border-radius: var(--la-r-block, 6px);
  cursor: pointer; place-items: center; transition: color 150ms ease, background-color 150ms ease;
}
.v-modal__close svg { width: 16px; height: 16px; stroke: currentColor; stroke-linecap: round; stroke-width: 1.7; }
.v-modal__close:hover { color: var(--la-blue, #184cff); background: rgba(var(--la-primary-rgb, 24, 76, 255), 0.08); }
.v-modal__close:active { background: rgba(var(--la-primary-rgb, 24, 76, 255), 0.14); }
.v-modal__close:focus-visible { outline: 2px solid rgba(var(--la-primary-rgb, 24, 76, 255), 0.35); outline-offset: 1px; }
.v-modal__close:disabled { cursor: not-allowed; opacity: 0.45; }
.v-modal__content { background: var(--la-bg-elevated, #fff); }
.v-modal__body { padding: 20px 16px; }
.v-modal__footer {
  display: flex; padding: 12px 16px; justify-content: flex-end; gap: 12px;
  background: var(--la-bg-subtle, #f8faff); border-top: 1px solid var(--la-separator, #e5eaf3);
}
</style>
