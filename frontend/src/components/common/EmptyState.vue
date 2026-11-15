<script setup lang="ts">
import LaIcon from './LaIcon.vue'

withDefaults(
  defineProps<{ title?: string; description?: string; icon?: string; compact?: boolean }>(),
  { title: '暂无数据', description: '', icon: 'apps', compact: false },
)
</script>

<template>
  <div
    role="status"
    class="flex flex-col items-center justify-center text-center px-6"
    :class="compact ? 'py-10' : 'py-20'"
  >
    <div
      class="w-[52px] h-[52px] rounded-full flex items-center justify-center mb-3.5"
      style="background: rgba(118, 118, 128, 0.08); color: rgba(60, 60, 67, 0.38)"
    >
      <LaIcon :name="icon" :size="23" :stroke-width="1.6" aria-hidden="true" />
    </div>
    <div class="text-[15px] font-semibold text-ink tracking-tight">{{ title }}</div>
    <div v-if="description" class="text-[12.5px] text-muted mt-1.5 max-w-[300px] leading-relaxed">
      {{ description }}
    </div>
    <div class="mt-4"><slot /></div>
  </div>
</template>
