<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NInput,
  NInputNumber,
  NSelect,
  NSpin,
  NSwitch,
  useDialog,
  useMessage,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { knowledgeApi, modelApi } from '@/api/knowledge'
import type { Dataset, ModelConfig } from '@/types'
import { formatDate } from '@/utils/format'
import VModal from '@/components/common/VModal/index.vue'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const rows = ref<Dataset[]>([])
const embedModels = ref<ModelConfig[]>([])
const keyword = ref('')
const showCreate = ref(false)
const saving = ref(false)

const form = reactive({
  name: '',
  description: '',
  embedding_model_id: null as string | null,
  chunk_size: 500,
  chunk_overlap: 50,
  split_strategy: 'fixed',
  separator: '\n\n',
  keep_heading: true,
  clean_whitespace: true,
})

const embedOptions = computed(() =>
  embedModels.value.map((m) => ({ label: `${m.display_name} · ${m.model_name}`, value: m.id })),
)

async function load() {
  loading.value = true
  try {
    const res = await knowledgeApi.datasets({ page: 1, page_size: 50, keyword: keyword.value })
    rows.value = res.items
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.name.trim()) {
    message.warning('请填写知识库名称')
    return
  }
  saving.value = true
  try {
    const ds = await knowledgeApi.createDataset({ ...form, embedding_model_id: form.embedding_model_id || null })
    message.success('知识库已创建')
    showCreate.value = false
    router.push(`/knowledge/${ds.id}`)
  } finally {
    saving.value = false
  }
}

function confirmDelete(d: Dataset) {
  dialog.warning({
    title: '删除知识库',
    content: `确认删除「${d.name}」？其下所有文档与切片都会被删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await knowledgeApi.deleteDataset(d.id)
      message.success('已删除')
      load()
    },
  })
}

onMounted(async () => {
  embedModels.value = (await modelApi.available()).filter((m) => m.model_type === 'embedding')
  await load()
})
</script>

<template>
  <div class="la-page">
    <PageHeader title="知识库" subtitle="上传文档、切片向量化，为 Agent 提供 RAG 能力">
      <template #actions>
        <NButton type="primary" @click="showCreate = true">
          <template #icon><LaIcon name="plus" :size="14" /></template>
          创建知识库
        </NButton>
      </template>
    </PageHeader>

    <div class="flex items-center gap-2 mb-3">
      <NInput v-model:value="keyword" placeholder="搜索知识库"  clearable class="la-search !w-[240px]"
        @keyup.enter="load" @clear="load">
        <template #prefix><LaIcon name="search" :size="14" class="text-[rgba(60,60,67,0.38)]" /></template>
      </NInput>
      <NButton @click="load">查询</NButton>
    </div>

    <div v-if="loading" class="la-card p-12 flex justify-center"><NSpin /></div>

    <EmptyState
      v-else-if="!rows.length"
      class="la-card"
      icon="book"
      title="还没有知识库"
      description="创建一个知识库并上传 PDF / DOCX / TXT 文档，完成索引后即可被 Agent 检索"
    >
      <NButton type="primary" @click="showCreate = true">创建知识库</NButton>
    </EmptyState>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      <div
        v-for="d in rows"
        :key="d.id"
        class="la-card p-4 hover:shadow-sm transition-shadow cursor-pointer group"
        @click="router.push(`/knowledge/${d.id}`)"
      >
        <div class="flex items-start gap-2.5">
          <span class="la-icon-tile w-9 h-9 shrink-0" style="background: linear-gradient(160deg, #55C8DB 0%, #30B0C7 100%)">
            <LaIcon name="database" :size="17" :stroke-width="2" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-medium text-ink truncate">{{ d.name }}</div>
            <div class="text-[11.5px] text-muted line-clamp-2 mt-0.5 h-[32px]">
              {{ d.description || '暂无描述' }}
            </div>
          </div>
          <button
            type="button"
            class="la-icon-btn-danger"
            :aria-label="'删除'"
            @click.stop="confirmDelete(d)"
          >
            <LaIcon name="trash" :size="14" />
          </button>
        </div>

        <div class="flex items-center gap-3 mt-3 text-[11.5px] text-muted">
          <span>{{ d.doc_count }} 文档</span>
          <span>{{ d.segment_count }} 切片</span>
          <span>Chunk {{ d.chunk_size }}/{{ d.chunk_overlap }}</span>
        </div>

        <div class="flex items-center justify-between mt-3 pt-3 border-t border-line">
          <StatusTag :status="d.index_status" />
          <span class="text-[11px] text-muted">{{ formatDate(d.updated_at, false) }}</span>
        </div>
      </div>
    </div>

    <VModal v-model:show="showCreate" title="创建知识库" :width="560">
      <div class="space-y-3">
        <div>
          <div class="text-[12.5px] text-muted mb-1">名称</div>
          <NInput v-model:value="form.name" placeholder="例如：产品手册" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">描述</div>
          <NInput v-model:value="form.description" type="textarea" :rows="2" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">Embedding 模型（向量化必需）</div>
          <NSelect
            v-model:value="form.embedding_model_id"
            :options="embedOptions"
            placeholder="选择 embedding 模型"
            clearable
          />
          <div v-if="!embedOptions.length" class="text-[11.5px] text-[#C86A00] mt-1">
            未配置 Embedding 模型，文档可以上传但无法向量化。请到
            <RouterLink to="/models" class="text-primary hover:underline">模型管理</RouterLink>
            添加 embedding 类型模型。
          </div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <div class="text-[12.5px] text-muted mb-1">Chunk Size</div>
            <NInputNumber v-model:value="form.chunk_size" :min="50" :max="4000" :step="50" class="!w-full" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Chunk Overlap</div>
            <NInputNumber v-model:value="form.chunk_overlap" :min="0" :max="1000" :step="10" class="!w-full" />
          </div>
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">切片策略</div>
          <NSelect
            v-model:value="form.split_strategy"
            :options="[
              { label: '固定长度', value: 'fixed' },
              { label: '按段落', value: 'paragraph' },
              { label: '按标题', value: 'heading' },
              { label: '自定义分隔符', value: 'separator' },
            ]"
          />
        </div>
        <div v-if="form.split_strategy === 'separator'">
          <div class="text-[12.5px] text-muted mb-1">分隔符</div>
          <NInput v-model:value="form.separator" placeholder="例如：\n\n 或 ###" />
        </div>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-[12.5px] text-ink">
            <NSwitch v-model:value="form.keep_heading" :round="false" /> 保留标题
          </label>
          <label class="flex items-center gap-2 text-[12.5px] text-ink">
            <NSwitch v-model:value="form.clean_whitespace" :round="false" /> 清理空白字符
          </label>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="create">创建</NButton>
        </div>
      </template>
    </VModal>
  </div>
</template>
