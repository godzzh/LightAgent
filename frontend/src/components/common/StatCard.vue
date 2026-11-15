<script setup lang="ts">
import { computed } from 'vue'
import LaIcon from './LaIcon.vue'

type Tone = 'blue' | 'green' | 'purple' | 'orange' | 'teal' | 'indigo'

const props = withDefaults(
  defineProps<{
    label: string
    value: number | string
    icon?: string
    suffix?: string
    loading?: boolean
    tone?: Tone
  }>(),
  { icon: 'chart', suffix: '', loading: false, tone: 'blue' },
)

/** iOS 系统色渐变，用于图标底 */
const tones: Record<Tone, string> = {
  blue: 'linear-gradient(160deg, #6B8CFF 0%, #184CFF 100%)',
  green: 'linear-gradient(160deg, #5BD97A 0%, #34C759 100%)',
  purple: 'linear-gradient(160deg, #C86BEC 0%, #AF52DE 100%)',
  orange: 'linear-gradient(160deg, #FFB03A 0%, #FF9500 100%)',
  teal: 'linear-gradient(160deg, #55C8DB 0%, #30B0C7 100%)',
  indigo: 'linear-gradient(160deg, #7B79E8 0%, #5856D6 100%)',
}

const accent = computed(() => tones[props.tone])
</script>

<template>
  <div class="la-card p-4 transition-shadow duration-300 hover:shadow-float">
    <div class="flex items-center gap-2">
      <span
        class="la-icon-tile w-[26px] h-[26px] shrink-0"
        :style="{ background: accent }"
      >
        <LaIcon :name="icon" :size="14" :stroke-width="2" />
      </span>
      <span class="text-[12.5px] text-muted truncate">{{ label }}</span>
    </div>

    <div class="mt-2.5 flex items-baseline gap-1">
      <span class="text-[26px] font-semibold text-ink leading-[32px] tabular-nums tracking-tight">
        {{ loading ? '—' : value }}
      </span>
      <span v-if="suffix" class="text-[12px] text-muted">{{ suffix }}</span>
    </div>
  </div>
</template>
