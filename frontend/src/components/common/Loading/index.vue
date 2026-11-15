<template>
  <div v-show="loading" class="la-loading" :class="'la-loading--' + size" ref="contentRef">
    <div class="la-loading__spin"><i></i><i></i><i></i><i></i></div>
    <span v-if="tip" class="la-loading__tip">{{ tip }}</span>
  </div>
</template>
<script setup lang="ts">
import { ref, watch } from 'vue'

const props = withDefaults(defineProps<{ loading?: boolean; tip?: string; size?: string }>(), {
  loading: false, tip: '', size: 'medium',
})
const contentRef = ref<HTMLElement | null>(null)

watch(() => props.loading, (v) => {
  const parent = contentRef.value?.parentNode
  if (!parent) return
  for (const child of Array.from(parent.children)) {
    (child as HTMLElement).style.opacity = v ? '0.48' : '1'
  }
})
</script>
<style scoped>
.la-loading {
  position: absolute; inset: 0; z-index: 1011;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 5px;
  cursor: wait; user-select: none; opacity: 1 !important;
}
.la-loading__spin { position: relative; display: inline-block; width: 22px; height: 22px; animation: la-spin 0.8s linear infinite; }
.la-loading__spin i { position: absolute; display: inline-block; width: 9px; height: 9px; border-radius: 50%; background: var(--la-blue, #184cff); }
.la-loading__spin i:nth-child(1) { top: 0; left: 0; }
.la-loading__spin i:nth-child(2) { top: 0; right: 0; opacity: .8; }
.la-loading__spin i:nth-child(3) { bottom: 0; left: 0; opacity: .5; }
.la-loading__spin i:nth-child(4) { bottom: 0; right: 0; opacity: .3; }
.la-loading__tip { margin-top: 4px; color: var(--la-blue, #184cff); font-size: 12px; }
.la-loading--small .la-loading__spin { width: 17px; height: 17px; }
.la-loading--small .la-loading__spin i { width: 7px; height: 7px; }
.la-loading--large .la-loading__spin { width: 28px; height: 28px; }
.la-loading--large .la-loading__spin i { width: 12px; height: 12px; }
@keyframes la-spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
