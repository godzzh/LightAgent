<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton,
  NDataTable,
  NDropdown,
  NEmpty,
  NInput,
  NModal,
  NSelect,
  NSpin,
  NTag,
  useDialog,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { appApi } from '@/api/auth'
import { modelApi } from '@/api/knowledge'
import type { Application, ModelConfig } from '@/types'
import { formatDate, truncate } from '@/utils/format'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

const loading = ref(false)
const rows = ref<Application[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const keyword = ref('')
const typeFilter = ref<string | null>(null)
const templates = ref<any[]>([])
const models = ref<ModelConfig[]>([])

const showCreate = ref(false)
const creating = ref(false)
const form = reactive({
  name: '',
  description: '',
  app_type: 'chat_agent',
  template: 'blank',
  model_config_id: null as string | null,
})

const typeOptions = [
  { label: '全部类型', value: '' },
  { label: 'Chat Agent', value: 'chat_agent' },
  { label: 'Chatbot', value: 'chatbot' },
  { label: 'Workflow 应用', value: 'workflow' },
]

const llmOptions = computed(() =>
  models.value
    .filter((m) => m.model_type === 'llm')
    .map((m) => ({ label: `${m.display_name} (${m.model_name})`, value: m.id })),
)

const templateOptions = computed(() =>
  templates.value.map((t) => ({ label: `${t.name} · ${t.description}`, value: t.key })),
)

const typeLabel: Record<string, string> = {
  chat_agent: 'Chat Agent',
  chatbot: 'Chatbot',
  workflow: 'Workflow',
}

function openApp(row: Application) {
  if (row.app_type === 'workflow') {
    if (row.workflow_id) router.push(`/workflows/${row.workflow_id}`)
    else router.push(`/applications/${row.id}/publish`)
    return
  }
  router.push(`/applications/${row.id}/agent`)
}

async function load() {
  loading.value = true
  try {
    const res = await appApi.list({
      page: page.value,
      page_size: pageSize.value,
      keyword: keyword.value,
      app_type: typeFilter.value || undefined,
    })
    rows.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

async function loadMeta() {
  const [tpl, mdl] = await Promise.all([appApi.templates(), modelApi.available()])
  templates.value = tpl
  models.value = mdl
  if (!form.model_config_id && llmOptions.value.length) {
    form.model_config_id = llmOptions.value[0].value as string
  }
}

async function create() {
  if (!form.name.trim()) {
    message.warning('请填写应用名称')
    return
  }
  creating.value = true
  try {
    const payload: Record<string, any> = {
      name: form.name.trim(),
      description: form.description,
      app_type: form.app_type,
      template: form.template,
      model_config_id: form.model_config_id,
    }
    const app = await appApi.create(payload)
    message.success('创建成功')
    showCreate.value = false
    form.name = ''
    form.description = ''
    if (app.app_type === 'workflow') {
      const { workflowApi } = await import('@/api/workflows')
      const wf = await workflowApi.create({ name: `${app.name} 流程` })
      await appApi.update(app.id, { workflow_id: wf.id })
      router.push(`/workflows/${wf.id}`)
    } else {
      router.push(`/applications/${app.id}/agent`)
    }
  } finally {
    creating.value = false
  }
}

async function doPublish(row: Application) {
  const res = await appApi.publish(row.id, { api_enabled: true, create_key: true })
  message.success('发布成功，已生成 API 访问密钥')
  if (res.api_key) {
    dialog.info({
      title: 'API Key 已生成',
      content: `请立即保存，密钥只展示这一次：\n${res.api_key}`,
      positiveText: '我已保存',
    })
  }
  load()
}

function confirmDelete(row: Application) {
  dialog.warning({
    title: '删除应用',
    content: `确认删除「${row.name}」？该操作不可恢复，相关会话与运行日志将一并删除。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await appApi.remove(row.id)
      message.success('已删除')
      load()
    },
  })
}

async function handleAction(key: string, row: Application) {
  if (key === 'open') return openApp(row)
  if (key === 'publish') return doPublish(row)
  if (key === 'unpublish') {
    await appApi.unpublish(row.id)
    message.success('已取消发布')
    return load()
  }
  if (key === 'copy') {
    await appApi.copy(row.id)
    message.success('已复制应用')
    return load()
  }
  if (key === 'logs') return router.push({ name: 'logs', query: { app: row.id } })
  if (key === 'publishPage') return router.push(`/applications/${row.id}/publish`)
  if (key === 'delete') return confirmDelete(row)
}

const actionOptions = (row: Application) => [
  { label: '进入调试', key: 'open', icon: () => h(LaIcon, { name: 'play' }) },
  { label: '发布设置', key: 'publishPage', icon: () => h(LaIcon, { name: 'globe' }) },
  row.status === 'published'
    ? { label: '取消发布', key: 'unpublish', icon: () => h(LaIcon, { name: 'close' }) }
    : { label: '快速发布', key: 'publish', icon: () => h(LaIcon, { name: 'upload' }) },
  { label: '复制应用', key: 'copy', icon: () => h(LaIcon, { name: 'copy' }) },
  { label: '运行日志', key: 'logs', icon: () => h(LaIcon, { name: 'history' }) },
  { type: 'divider', key: 'd1' },
  { label: '删除', key: 'delete', icon: () => h(LaIcon, { name: 'trash' }) },
]

const columns = computed<DataTableColumns<Application>>(() => [
  {
    title: '应用',
    key: 'name',
    minWidth: 220,
    render: (row) =>
      h('div', { class: 'flex items-center gap-2.5 cursor-pointer', onClick: () => openApp(row) }, [
        h(
          'div',
          {
            class: 'w-8 h-8 rounded-[9px] flex items-center justify-center text-white shrink-0',
            style:
              row.app_type === 'workflow'
                ? 'background:linear-gradient(160deg,#7B79E8 0%,#5856D6 100%);box-shadow:0 1px 3px rgba(0,0,0,0.12)'
                : 'background:linear-gradient(160deg,#4BA3FF 0%,#007AFF 100%);box-shadow:0 1px 3px rgba(0,0,0,0.12)',
          },
          [h(LaIcon, { name: row.app_type === 'workflow' ? 'flow' : 'robot', size: 15, strokeWidth: 2 })],
        ),
        h('div', { class: 'min-w-0' }, [
          h('div', { class: 'text-[13.5px] text-ink font-medium truncate tracking-tight' }, row.name),
          h('div', { class: 'text-[11.5px] text-muted truncate max-w-[280px] mt-0.5' }, row.description || '—'),
        ]),
      ]),
  },
  {
    title: '类型',
    key: 'app_type',
    width: 110,
    render: (row) =>
      h(
        'span',
        {
          class: 'la-pill',
          style: 'color:#8E8E93;background:rgba(142,142,147,0.12)',
        },
        typeLabel[row.app_type] || row.app_type,
      ),
  },
  {
    title: '模型',
    key: 'model_config_id',
    width: 150,
    render: (row) => {
      const m = models.value.find((x) => x.id === (row.model_config_id || row.config?.model_config_id))
      return h('span', { class: 'text-[12.5px] text-[rgba(60,60,67,0.7)]' }, m ? m.display_name : '—')
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render: (row) => h(StatusTag, { status: row.status }),
  },
  {
    title: '运行次数',
    key: 'run_count',
    width: 90,
    render: (row) => h('span', { class: 'text-[12.5px] text-[rgba(60,60,67,0.7)]' }, String(row.run_count || 0)),
  },
  {
    title: '更新时间',
    key: 'updated_at',
    width: 150,
    render: (row) => h('span', { class: 'text-[12.5px] text-muted' }, formatDate(row.updated_at)),
  },
  {
    title: '',
    key: 'actions',
    width: 60,
    align: 'right',
    render: (row) =>
      h(
        NDropdown,
        { options: actionOptions(row), trigger: 'click', onSelect: (k: string) => handleAction(k, row) },
        { default: () => h(NButton, { size: 'tiny', quaternary: true }, { icon: () => h(LaIcon, { name: 'more' }) }) },
      ),
  },
])

onMounted(async () => {
  await Promise.all([load(), loadMeta()])
})
</script>

<template>
  <div class="la-page">
    <PageHeader title="应用管理" subtitle="创建、调试与发布你的 AI 应用">
      <template #actions>
        <NButton type="primary" size="small" @click="showCreate = true">
          <template #icon><LaIcon name="plus" :size="14" /></template>
          新建应用
        </NButton>
      </template>
    </PageHeader>

    <div class="la-card">
      <div class="flex flex-wrap items-center gap-2 p-3">
        <NInput
          v-model:value="keyword"
          placeholder="搜索应用名称"
          clearable
          size="small"
          class="la-search !w-[240px]"
          @keyup.enter="((page = 1), load())"
          @clear="((page = 1), load())"
        >
          <template #prefix><LaIcon name="search" :size="14" class="text-[rgba(60,60,67,0.38)]" /></template>
        </NInput>
        <NSelect
          :options="typeOptions"
          size="small"
          class="!w-[140px]"
          :value="typeFilter || ''"
          @update:value="(v: string) => { typeFilter = v || null; page = 1; load() }"
        />
        <div class="flex-1"></div>
        <span class="text-[12px] text-muted">共 {{ total }} 个应用</span>
      </div>

      <NDataTable
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: Application) => r.id"
        :bordered="false"
        :single-line="false"
        size="small"
        :pagination="{
          page,
          pageSize,
          itemCount: total,
          showSizePicker: true,
          pageSizes: [10, 20, 50],
          onUpdatePage: (p: number) => { page = p; load() },
          onUpdatePageSize: (s: number) => { pageSize = s; page = 1; load() },
        }"
      >
        <template #empty>
          <NEmpty description="还没有应用">
            <template #extra>
              <NButton size="small" type="primary" @click="showCreate = true">创建第一个应用</NButton>
            </template>
          </NEmpty>
        </template>
      </NDataTable>
    </div>

    <!-- 新建应用 -->
    <NModal
      v-model:show="showCreate"
      preset="card"
      title="新建应用"
      class="!w-[560px]"
      :bordered="false"
    >
      <div class="space-y-3">
        <div>
          <div class="text-[12.5px] text-muted mb-1">应用名称</div>
          <NInput v-model:value="form.name" placeholder="例如：售后客服助手" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">应用类型</div>
          <NSelect
            v-model:value="form.app_type"
            :options="[
              { label: 'Chat Agent（可配置工具与知识库）', value: 'chat_agent' },
              { label: 'Chatbot（基础对话）', value: 'chatbot' },
              { label: 'Workflow 应用（可视化编排）', value: 'workflow' },
            ]"
          />
        </div>
        <div v-if="form.app_type !== 'workflow'">
          <div class="text-[12.5px] text-muted mb-1">选择模板</div>
          <NSelect v-model:value="form.template" :options="templateOptions" />
        </div>
        <div v-if="form.app_type !== 'workflow'">
          <div class="text-[12.5px] text-muted mb-1">默认模型</div>
          <NSelect
            v-model:value="form.model_config_id"
            :options="llmOptions"
            placeholder="选择模型（可稍后配置）"
            clearable
          />
          <div v-if="!llmOptions.length" class="text-[11.5px] text-[#C86A00] mt-1">
            尚未配置 LLM 模型，请先到「模型管理」添加 DeepSeek 等模型
          </div>
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">描述（可选）</div>
          <NInput v-model:value="form.description" type="textarea" :rows="2" placeholder="简要说明应用用途" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton size="small" @click="showCreate = false">取消</NButton>
          <NButton size="small" type="primary" :loading="creating" @click="create">创建</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>
