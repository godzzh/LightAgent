<script setup lang="ts">
import { computed } from 'vue'
import { useMessage } from 'naive-ui'
import type { ChatMessageItem } from '@/types'
import { renderMarkdown } from '@/utils/markdown'
import LaIcon from '@/components/common/LaIcon.vue'

const props = defineProps<{ message: ChatMessageItem }>()
const msgApi = useMessage()

const isUser = computed(() => props.message.role === 'user')
const html = computed(() => renderMarkdown(props.message.content))

async function copy() {
  try {
    await navigator.clipboard.writeText(props.message.content || '')
    msgApi.success('已复制')
  } catch {
    msgApi.error('复制失败，请手动选择文本')
  }
}
</script>

<template>
  <div class="flex gap-2.5 la-enter" :class="isUser ? 'flex-row-reverse' : ''">
    <div
      class="w-7 h-7 rounded-[6px] shrink-0 flex items-center justify-center text-white mt-0.5"
      :style="{
        background: isUser
          ? 'linear-gradient(160deg,#8E8E93 0%,#636366 100%)'
          : 'linear-gradient(160deg,#6B8CFF 0%,#184CFF 100%)',
      }"
    >
      <LaIcon :name="isUser ? 'user' : 'sparkles'" :size="14" :stroke-width="2" />
    </div>

    <div class="max-w-[calc(100%-44px)] min-w-0">
      <div
        class="px-3.5 py-2.5 text-[13.5px] leading-[1.55]"
        :class="isUser ? 'text-white' : 'text-ink'"
        :style="
          isUser
            ? 'background:#184CFF;border-radius:8px;box-shadow:0 1px 2px rgba(24,76,255,0.2)'
            : 'background:#FFFFFF;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,0.04),0 6px 18px -12px rgba(0,0,0,0.14)'
        "
      >
        <div v-if="isUser" class="whitespace-pre-wrap break-words">{{ message.content }}</div>
        <div v-else>
          <div v-if="message.error" role="alert" aria-live="polite" class="flex items-start gap-2 text-[13px]" style="color: var(--la-error-text)">
            <LaIcon name="warn" :size="15" class="mt-0.5" />
            <span>{{ message.error }}</span>
          </div>
          <template v-else>
            <div v-if="!message.content && message.streaming" class="la-typing py-1.5">
              <i></i><i></i><i></i>
            </div>
            <div v-else class="la-markdown" v-html="html"></div>
            <span v-if="message.streaming" class="la-caret"></span>
          </template>
        </div>
      </div>

      <!-- 引用来源 -->
      <div v-if="message.meta?.knowledge?.length" class="mt-1.5 space-y-1">
        <div class="text-[11px] text-muted flex items-center gap-1">
          <LaIcon name="book" :size="12" />
          召回 {{ message.meta.knowledge.length }} 个知识片段
        </div>
        <div class="flex flex-wrap gap-1.5">
          <span
            v-for="(k, i) in message.meta.knowledge"
            :key="k.segment_id"
            class="text-[11px] px-2 py-1 rounded-[6px] cursor-help"
            style="background: rgba(24,76,255,0.1); color: #184cff"
            :title="k.content"
          >
            [{{ i + 1 }}] {{ k.document_name }} · {{ k.score.toFixed(2) }}
          </span>
        </div>
      </div>

      <!-- 工具调用 -->
      <div v-if="message.meta?.toolCalls?.length" class="mt-1.5 space-y-1">
        <div
          v-for="(t, i) in message.meta.toolCalls"
          :key="i"
          class="text-[11.5px] rounded-[6px] px-2.5 py-2"
          style="background: rgba(118, 118, 128, 0.07); color: rgba(60, 60, 67, 0.72)"
        >
          <div class="flex items-center gap-1 font-medium">
            <LaIcon name="tool" :size="12" />
            {{ t.name }}
            <span v-if="t.error" style="color: #ff3b30">· 失败</span>
          </div>
          <div class="text-[11px] text-muted mt-0.5 break-all">
            入参 {{ JSON.stringify(t.arguments) }}
          </div>
          <div v-if="t.error" class="text-[11px] mt-0.5" style="color: #ff3b30">{{ t.error }}</div>
        </div>
      </div>

      <div class="flex items-center gap-3 mt-1.5 px-1 text-[11px] text-muted" :class="isUser ? 'justify-end' : ''">
        <span v-if="message.created_at">{{ new Date(message.created_at).toLocaleTimeString('zh-CN') }}</span>
        <span v-if="message.meta?.usage?.total_tokens">{{ message.meta.usage.total_tokens }} tokens</span>
        <span v-if="message.meta?.duration_ms">{{ (message.meta.duration_ms / 1000).toFixed(2) }}s</span>
        <button v-if="message.content" class="hover:text-primary flex items-center gap-0.5 ios-press" @click="copy">
          <LaIcon name="copy" :size="11" /> 复制
        </button>
      </div>
    </div>
  </div>
</template>
