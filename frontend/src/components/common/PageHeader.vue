<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <div class="la-enter flex items-end justify-between gap-4 mb-6">
    <div class="min-w-0">
      <h1 class="la-title truncate">{{ title }}</h1>
      <p v-if="subtitle" class="la-subtitle mt-1">{{ subtitle }}</p>
    </div>
    <div class="flex items-center gap-2 shrink-0 pb-0.5">
      <slot name="actions" />
    </div>
  </div>
</template>
