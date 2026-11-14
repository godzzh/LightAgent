<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NModal, NSpin, useDialog, useMessage } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { workflowApi } from '@/api/workflows'
import type { Workflow } from '@/types'
import { formatDate } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const rows = ref<Workflow[]>([])
const showCreate = ref(false)
const creating = ref(false)
const form = reactive({ name: '', description: '' })

async function load() {
  loading.value = true
  try {
    const res = await workflowApi.list({ page: 1, page_size: 50 })
    rows.value = res.items
  } finally {
    loading.value = false
  }
}

async function create() {
  if (!form.name.trim()) {
    message.warning('请填写工作流名称')
    return
  }
  creating.value = true
  try {
    const wf = await workflowApi.create({ name: form.name.trim(), description: form.description })
    showCreate.value = false
    form.name = ''
    form.description = ''
    router.push(`/workflows/${wf.id}`)
  } finally {
    creating.value = false
  }
}

function remove(wf: Workflow) {
  dialog.warning({
    title: '删除工作流',
    content: `确认删除「${wf.name}」？运行记录将一并删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await workflowApi.remove(wf.id)
      message.success('已删除')
      load()
    },
  })
}

onMounted(load)
</script>

<template>
  <div class="la-page max-w-[1300px]">
    <PageHeader title="工作流" subtitle="可视化编排节点，后端 DAG 引擎真实执行">
      <template #actions>
        <NButton size="small" type="primary" @click="showCreate = true">
          <template #icon><LaIcon name="plus" :size="14" /></template>
          创建工作流
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="la-card p-12 flex justify-center"><NSpin /></div>

    <EmptyState
      v-else-if="!rows.length"
      class="la-card"
      icon="flow"
      title="还没有工作流"
      description="从 Start → LLM → Answer 搭一条最小链路，体验真实的节点执行与变量传递"
    >
      <NButton type="primary" size="small" @click="showCreate = true">创建工作流</NButton>
    </EmptyState>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      <div
        v-for="wf in rows"
        :key="wf.id"
        class="la-card p-4 hover:shadow-sm transition-shadow cursor-pointer group"
        @click="router.push(`/workflows/${wf.id}`)"
      >
        <div class="flex items-start gap-2.5">
          <span class="la-icon-tile w-9 h-9 shrink-0" style="background: linear-gradient(160deg, #7B79E8 0%, #5856D6 100%)">
            <LaIcon name="flow" :size="17" :stroke-width="2" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-medium text-ink truncate">{{ wf.name }}</div>
            <div class="text-[11.5px] text-muted line-clamp-2 mt-0.5 h-[32px]">
              {{ wf.description || '暂无描述' }}
            </div>
          </div>
          <button class="opacity-0 group-hover:opacity-100 text-muted hover:text-[#FF3B30]" @click.stop="remove(wf)">
            <LaIcon name="trash" :size="14" />
          </button>
        </div>
        <div class="flex items-center justify-between mt-3 pt-3 border-t border-line text-[11px] text-muted">
          <span>{{ wf.graph?.nodes?.length || 0 }} 个节点 · v{{ wf.version }}</span>
          <span>运行 {{ wf.run_count || 0 }} 次</span>
          <span>{{ formatDate(wf.updated_at, false) }}</span>
        </div>
      </div>
    </div>

    <NModal v-model:show="showCreate" preset="card" title="创建工作流" class="!w-[480px]" :bordered="false">
      <div class="space-y-3">
        <div>
          <div class="text-[12.5px] text-muted mb-1">名称</div>
          <NInput v-model:value="form.name" placeholder="例如：客服工单分类" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">描述</div>
          <NInput v-model:value="form.description" type="textarea" :rows="2" />
        </div>
        <div class="text-[11.5px] text-muted">
          创建后会自动生成 Start → End 的基础画布，你可以继续添加 LLM、条件分支等节点。
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="showCreate = false">取消</NButton>
          <NButton size="small" type="primary" :loading="creating" @click="create">创建并编辑</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
