<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NDrawer,
  NDrawerContent,
  NInput,
  NInputNumber,
  NPagination,
  NSpin,
  NTabPane,
  NTabs,
  useDialog,
  useMessage,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { knowledgeApi } from '@/api/knowledge'
import type { Dataset, KDocument, RetrieveHit, Segment } from '@/types'
import { formatDate, formatSize } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const datasetId = computed(() => route.params.id as string)
const dataset = ref<Dataset | null>(null)
const documents = ref<KDocument[]>([])
const loading = ref(true)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const tab = ref('documents')
let timer: number | null = null

const retrieveQuery = ref('')
const retrieving = ref(false)
const hits = ref<RetrieveHit[]>([])
const retrieveMsg = ref('')
const topK = ref(4)
const threshold = ref(0.3)

const showSegments = ref(false)
const segments = ref<Segment[]>([])
const segTotal = ref(0)
const segPage = ref(1)
const segDocId = ref('')
const segLoading = ref(false)

async function loadDataset() {
  dataset.value = await knowledgeApi.dataset(datasetId.value)
}

async function loadDocs(silent = false) {
  if (!silent) loading.value = true
  try {
    const res = await knowledgeApi.documents(datasetId.value, { page: 1, page_size: 100 })
    documents.value = res.items
  } finally {
    loading.value = false
  }
}

function anyProcessing() {
  return documents.value.some((d) => ['waiting', 'parsing', 'splitting', 'indexing'].includes(d.status))
}

function setupPolling() {
  if (timer) window.clearInterval(timer)
  timer = window.setInterval(async () => {
    if (anyProcessing()) {
      await loadDocs(true)
      await loadDataset()
    }
  }, 2000)
}

function pickFile() {
  fileInput.value?.click()
}

async function onFileChange(e: Event) {
  const files = (e.target as HTMLInputElement).files
  if (!files?.length) return
  uploading.value = true
  try {
    for (const file of Array.from(files)) {
      await knowledgeApi.upload(datasetId.value, file)
    }
    message.success('上传成功，正在后台解析与向量化')
    await loadDocs()
    await loadDataset()
  } finally {
    uploading.value = false
    if (fileInput.value) fileInput.value.value = ''
  }
}

async function reindex(doc: KDocument) {
  await knowledgeApi.reindex(doc.id)
  message.success('已重新加入处理队列')
  loadDocs()
}

function removeDoc(doc: KDocument) {
  dialog.warning({
    title: '删除文档',
    content: `确认删除「${doc.name}」及其所有切片？`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await knowledgeApi.deleteDocument(doc.id)
      message.success('已删除')
      loadDocs()
      loadDataset()
    },
  })
}

async function openSegments(doc: KDocument) {
  segDocId.value = doc.id
  segPage.value = 1
  showSegments.value = true
  await loadSegments()
}

async function loadSegments() {
  segLoading.value = true
  try {
    const res = await knowledgeApi.segments(segDocId.value, { page: segPage.value, page_size: 10 })
    segments.value = res.items
    segTotal.value = res.total
  } finally {
    segLoading.value = false
  }
}

async function doRetrieve() {
  if (!retrieveQuery.value.trim()) {
    message.warning('请输入检索问题')
    return
  }
  retrieving.value = true
  retrieveMsg.value = ''
  try {
    const res = await knowledgeApi.retrieve({
      query: retrieveQuery.value,
      dataset_ids: [datasetId.value],
      top_k: topK.value,
      threshold: threshold.value,
    })
    hits.value = res.results
    retrieveMsg.value = res.fallback ? res.message || '已降级为关键词检索' : ''
  } finally {
    retrieving.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadDataset(), loadDocs()])
  setupPolling()
})

onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div class="la-page">
    <PageHeader
      :title="dataset?.name || '知识库详情'"
      :subtitle="dataset?.description || '管理文档、切片与检索测试'"
    >
      <template #actions>
        <NButton @click="router.push('/knowledge')">返回列表</NButton>
        <NButton type="primary" :loading="uploading" @click="pickFile">
          <template #icon><LaIcon name="upload" :size="14" /></template>
          上传文档
        </NButton>
        <input ref="fileInput" type="file" multiple class="hidden" accept=".pdf,.docx,.txt,.md,.html" @change="onFileChange" />
      </template>
    </PageHeader>

    <div v-if="dataset" class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
      <div class="la-card p-3">
        <div class="text-[11.5px] text-muted">索引状态</div>
        <div class="mt-1"><StatusTag :status="dataset.index_status" /></div>
      </div>
      <div class="la-card p-3">
        <div class="text-[11.5px] text-muted">文档 / 切片</div>
        <div class="text-[15px] font-medium text-ink mt-1">{{ dataset.doc_count }} / {{ dataset.segment_count }}</div>
      </div>
      <div class="la-card p-3">
        <div class="text-[11.5px] text-muted">切片策略</div>
        <div class="text-[13px] text-ink mt-1">
          {{ { fixed: '固定长度', paragraph: '按段落', heading: '按标题', separator: '自定义分隔符' }[dataset.split_strategy] }}
          · {{ dataset.chunk_size }}/{{ dataset.chunk_overlap }}
        </div>
      </div>
      <div class="la-card p-3">
        <div class="text-[11.5px] text-muted">创建时间</div>
        <div class="text-[13px] text-ink mt-1">{{ formatDate(dataset.created_at, false) }}</div>
      </div>
    </div>

    <div class="la-card">
      <NTabs v-model:value="tab" type="line" class="px-4 pt-1">
        <NTabPane name="documents" tab="文档">
          <div v-if="loading" class="py-12 flex justify-center"><NSpin /></div>
          <EmptyState
            v-else-if="!documents.length"
            icon="upload"
            title="还没有文档"
            description="支持 PDF / DOCX / TXT / Markdown / HTML，上传后自动解析切片与向量化"
          >
            <NButton type="primary" :loading="uploading" @click="pickFile">上传文档</NButton>
          </EmptyState>
          <div v-else class="divide-y divide-[rgba(118,118,128,0.08)] pb-2">
            <div v-for="doc in documents" :key="doc.id" class="flex flex-wrap items-center gap-3 py-2.5">
              <span class="w-8 h-8 rounded-[6px] bg-[#F7F7F9] text-[#8E8E93] flex items-center justify-center">
                <LaIcon name="book" :size="15" />
              </span>
              <div class="min-w-0 flex-1">
                <div class="text-[13px] text-ink truncate">{{ doc.name }}</div>
                <div class="text-[11px] text-muted">
                  {{ formatSize(doc.file_size) }} · {{ doc.chunk_count }} 切片 ·
                  {{ doc.char_count }} 字符
                </div>
                <div v-if="['parsing','splitting','indexing','waiting'].includes(doc.status)" class="mt-1 w-40 h-1 bg-[rgba(118,118,128,0.08)] rounded">
                  <div class="h-1 bg-primary rounded transition-all" :style="{ width: `${doc.progress}%` }"></div>
                </div>
                <div v-if="doc.error" class="text-[11px] text-[#FF3B30] mt-0.5 max-w-md truncate">{{ doc.error }}</div>
              </div>
              <StatusTag :status="doc.status" />
              <NButton quaternary :disabled="doc.status !== 'completed'" @click="openSegments(doc)">
                切片
              </NButton>
              <NButton quaternary @click="reindex(doc)">
                <template #icon><LaIcon name="refresh" :size="12" /></template>
              </NButton>
              <NButton quaternary @click="removeDoc(doc)">
                <template #icon><LaIcon name="trash" :size="12" /></template>
              </NButton>
            </div>
          </div>
        </NTabPane>

        <NTabPane name="retrieve" tab="检索测试">
          <div class="pb-4 pt-1">
            <div class="flex flex-wrap items-end gap-2">
              <div class="flex-1 min-w-[260px]">
                <div class="text-[12.5px] text-muted mb-1">检索问题</div>
                <NInput v-model:value="retrieveQuery" placeholder="输入问题，测试向量召回效果" @keyup.enter="doRetrieve" />
              </div>
              <div class="w-[100px]">
                <div class="text-[12.5px] text-muted mb-1">Top K</div>
                <NInputNumber v-model:value="topK" :min="1" :max="20" class="!w-full" />
              </div>
              <div class="w-[120px]">
                <div class="text-[12.5px] text-muted mb-1">阈值</div>
                <NInputNumber v-model:value="threshold" :min="0" :max="1" :step="0.05" class="!w-full" />
              </div>
              <NButton type="primary" :loading="retrieving" @click="doRetrieve">检索</NButton>
            </div>

            <div v-if="retrieveMsg" class="text-[11.5px] text-[#C86A00] mt-2">{{ retrieveMsg }}</div>

            <div v-if="retrieving" class="py-10 flex justify-center"><NSpin /></div>
            <EmptyState
              v-else-if="!hits.length"
              compact
              icon="search"
              title="暂无结果"
              description="输入问题后执行检索，结果会展示文档来源、匹配文本与相似度"
            />
            <div v-else class="space-y-2 mt-3">
              <div v-for="(h, i) in hits" :key="h.segment_id" class="border border-line rounded-[8px] p-3">
                <div class="flex items-center justify-between gap-2">
                  <div class="text-[12.5px] font-medium text-ink">
                    [{{ i + 1 }}] {{ h.document_name }}
                    <span class="text-[11px] text-muted font-normal">#{{ h.position }}</span>
                  </div>
                  <span class="text-[11.5px] font-mono text-[#184CFF]">{{ h.score.toFixed(4) }}</span>
                </div>
                <div class="text-[12.5px] text-[rgba(60,60,67,0.7)] mt-1.5 whitespace-pre-wrap line-clamp-5">{{ h.content }}</div>
              </div>
            </div>
          </div>
        </NTabPane>

        <NTabPane name="settings" tab="切片配置">
          <div class="pb-6 pt-1 max-w-lg text-[12.5px] text-[rgba(60,60,67,0.7)] leading-6">
            <div class="grid grid-cols-2 gap-3">
              <div class="border border-line rounded-[8px] p-3">
                <div class="text-[11.5px] text-muted">切片策略</div>
                <div class="text-ink mt-0.5">{{ dataset?.split_strategy }}</div>
              </div>
              <div class="border border-line rounded-[8px] p-3">
                <div class="text-[11.5px] text-muted">Chunk Size / Overlap</div>
                <div class="text-ink mt-0.5">{{ dataset?.chunk_size }} / {{ dataset?.chunk_overlap }}</div>
              </div>
              <div class="border border-line rounded-[8px] p-3">
                <div class="text-[11.5px] text-muted">保留标题</div>
                <div class="text-ink mt-0.5">{{ dataset?.keep_heading ? '是' : '否' }}</div>
              </div>
              <div class="border border-line rounded-[8px] p-3">
                <div class="text-[11.5px] text-muted">清理空白</div>
                <div class="text-ink mt-0.5">{{ dataset?.clean_whitespace ? '是' : '否' }}</div>
              </div>
            </div>
            <div class="mt-3 text-muted">
              修改配置后需要重新索引已有文档才会生效（文档列表中点击刷新图标）。
            </div>
          </div>
        </NTabPane>
      </NTabs>
    </div>

    <!-- 切片抽屉 -->
    <NDrawer v-model:show="showSegments" :width="620" placement="right">
      <NDrawerContent title="文档切片" closable>
        <div v-if="segLoading" class="py-10 flex justify-center"><NSpin /></div>
        <div v-else class="space-y-2">
          <div v-for="s in segments" :key="s.id" class="border border-line rounded-[8px] p-3">
            <div class="flex items-center justify-between text-[11.5px] text-muted">
              <span>#{{ s.position }} · {{ s.tokens }} tokens</span>
              <span v-if="s.has_embedding" class="text-[#248A3D]">已向量化</span>
              <span v-else class="text-[#C86A00]">无向量</span>
            </div>
            <div class="text-[12.5px] text-[rgba(60,60,67,0.7)] mt-1.5 whitespace-pre-wrap">{{ s.content }}</div>
          </div>
        </div>
        <template #footer>
          <NPagination
            v-model:page="segPage"
            :item-count="segTotal"
            :page-size="10"
            @update:page="loadSegments"
          />
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>
