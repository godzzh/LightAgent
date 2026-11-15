<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import {
  NButton,
  NInput,
  NInputNumber,
  NSelect,
  NSpin,
  NSwitch,
  NTag,
  useDialog,
  useMessage,
} from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { modelApi } from '@/api/knowledge'
import type { ModelConfig, ModelProvider } from '@/types'
import VModal from '@/components/common/VModal/index.vue'

const message = useMessage()
const dialog = useDialog()

const loading = ref(true)
const providers = ref<ModelProvider[]>([])
const presets = ref<any[]>([])
const testing = ref<string | null>(null)
const testResult = ref<Record<string, string>>({})

const showProvider = ref(false)
const showModel = ref(false)
const saving = ref(false)

const providerForm = reactive({
  name: '',
  provider_type: 'deepseek',
  base_url: 'https://api.deepseek.com/v1',
  api_key: '',
  is_default: true,
  remark: '',
})

const modelForm = reactive({
  provider_id: '',
  display_name: '',
  model_name: 'deepseek-chat',
  model_type: 'llm' as 'llm' | 'embedding',
  temperature: 0.7,
  top_p: 1,
  max_tokens: 2048,
  context_window: 32768,
  supports_streaming: true,
  supports_tool_call: true,
  is_default: true,
  remark: '',
})

const presetOptions = computed(() =>
  presets.value.map((p) => ({ label: `${p.name} (${p.type})`, value: p.type, base_url: p.base_url })),
)

const allModels = computed(() => providers.value.flatMap((p) => (p.configs || []).map((c) => ({ ...c, providerName: p.name }))))

function onPresetChange(type: string) {
  const preset = presets.value.find((p) => p.type === type)
  providerForm.provider_type = type
  if (preset) {
    providerForm.name = preset.name
    providerForm.base_url = preset.base_url
  }
}

async function load() {
  loading.value = true
  try {
    providers.value = await modelApi.providers()
  } finally {
    loading.value = false
  }
}

async function createProvider() {
  if (!providerForm.name.trim() || !providerForm.api_key.trim()) {
    message.warning('请填写名称与 API Key')
    return
  }
  saving.value = true
  try {
    await modelApi.createProvider({ ...providerForm })
    message.success('供应商已添加')
    showProvider.value = false
    providerForm.api_key = ''
    await load()
  } finally {
    saving.value = false
  }
}

async function testProvider(p: ModelProvider) {
  testing.value = p.id
  testResult.value = { ...testResult.value, [p.id]: '' }
  try {
    const res = await modelApi.test({ provider_id: p.id })
    testResult.value = { ...testResult.value, [p.id]: `${res.ok ? '✅' : '❌'} ${res.message}` }
    if (res.ok) message.success('连接成功')
    else message.error(res.message)
  } catch (e: any) {
    testResult.value = { ...testResult.value, [p.id]: `❌ ${e.message}` }
  } finally {
    testing.value = null
  }
}

function openModel(p?: ModelProvider) {
  const target = p || providers.value[0]
  if (!target) {
    message.warning('请先添加模型供应商')
    return
  }
  modelForm.provider_id = target.id
  modelForm.display_name = 'DeepSeek Chat'
  modelForm.model_name = 'deepseek-chat'
  modelForm.model_type = 'llm'
  showModel.value = true
}

async function createModel() {
  if (!modelForm.display_name || !modelForm.model_name) {
    message.warning('请填写模型显示名与模型名')
    return
  }
  saving.value = true
  try {
    await modelApi.createConfig({ ...modelForm })
    message.success('模型已添加')
    showModel.value = false
    await load()
  } finally {
    saving.value = false
  }
}

function confirmDeleteProvider(p: ModelProvider) {
  dialog.warning({
    title: '删除供应商',
    content: `确认删除「${p.name}」？其下所有模型配置将一并删除，已绑定该模型的应用将无法调用。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await modelApi.deleteProvider(p.id)
      message.success('已删除')
      load()
    },
  })
}

async function toggleModel(m: ModelConfig & { providerName?: string }) {
  await modelApi.updateConfig(m.id, { enabled: !m.enabled })
  load()
}

async function setDefault(m: ModelConfig) {
  await modelApi.updateConfig(m.id, { is_default: true })
  message.success('已设为默认模型')
  load()
}

onMounted(async () => {
  presets.value = await modelApi.presets()
  await load()
})
</script>

<template>
  <div class="la-page">
    <PageHeader title="模型管理" subtitle="统一 Provider 架构，支持 DeepSeek / OpenAI 及兼容接口">
      <template #actions>
        <NButton @click="showProvider = true">
          <template #icon><LaIcon name="plus" :size="14" /></template>
          添加供应商
        </NButton>
        <NButton type="primary" :disabled="!providers.length" @click="openModel()">
          添加模型
        </NButton>
      </template>
    </PageHeader>

    <div v-if="loading" class="la-card p-12 flex justify-center"><NSpin /></div>

    <template v-else>
      <EmptyState
        v-if="!providers.length"
        icon="cpu"
        title="还没有配置模型供应商"
        description="添加 DeepSeek 供应商并填入 API Key，即可开始真实模型调用"
      >
        <NButton type="primary" @click="showProvider = true">添加 DeepSeek</NButton>
      </EmptyState>

      <div v-else class="space-y-3">
        <div v-for="p in providers" :key="p.id" class="la-card overflow-hidden">
          <div class="flex flex-wrap items-center gap-3 px-4 h-14 border-b border-line">
            <span class="w-8 h-8 rounded-[6px] bg-[rgba(24,76,255,0.09)] text-primary flex items-center justify-center">
              <LaIcon name="cpu" :size="15" />
            </span>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="text-[13.5px] font-medium text-ink">{{ p.name }}</span>
                <NTag :bordered="false">{{ p.provider_type }}</NTag>
                <NTag v-if="p.is_default" :bordered="false" type="success">默认</NTag>
                <NTag v-if="!p.enabled" :bordered="false" type="warning">已禁用</NTag>
              </div>
              <div class="text-[11.5px] text-muted mt-0.5">
                {{ p.base_url || '默认地址' }} · Key {{ p.api_key_masked || '未配置' }}
              </div>
            </div>
            <div class="flex-1"></div>
            <span v-if="testResult[p.id]" class="text-[11.5px]">{{ testResult[p.id] }}</span>
            <NButton :loading="testing === p.id" @click="testProvider(p)">测试连接</NButton>
            <NButton @click="openModel(p)">添加模型</NButton>
            <NButton quaternary @click="confirmDeleteProvider(p)">
              <template #icon><LaIcon name="trash" :size="13" /></template>
            </NButton>
          </div>

          <div v-if="!p.configs?.length" class="px-4 py-4 text-[12.5px] text-muted">
            尚未添加模型配置。点击「添加模型」为该供应商登记模型（如 deepseek-chat / deepseek-reasoner）。
          </div>
          <div v-else class="divide-y divide-[rgba(118,118,128,0.08)]">
            <div
              v-for="m in p.configs"
              :key="m.id"
              class="flex flex-wrap items-center gap-3 px-4 py-2.5"
            >
              <div class="w-[180px] min-w-0">
                <div class="text-[13px] text-ink truncate">{{ m.display_name }}</div>
                <div class="text-[11px] text-muted font-mono truncate">{{ m.model_name }}</div>
              </div>
              <NTag :bordered="false" :type="m.model_type === 'embedding' ? 'info' : 'default'">
                {{ m.model_type === 'embedding' ? 'Embedding' : 'LLM' }}
              </NTag>
              <span class="text-[11.5px] text-muted">
                T={{ m.temperature }} · {{ m.max_tokens }} tokens
              </span>
              <span v-if="m.supports_tool_call" class="text-[11px] text-[#248A3D]">Tool Calling</span>
              <div class="flex-1"></div>
              <NButton v-if="!m.is_default" quaternary @click="setDefault(m)">设为默认</NButton>
              <NTag v-else :bordered="false" type="success">默认</NTag>
              <NSwitch :value="m.enabled" @update:value="toggleModel(m)" :round="false" />
              <NButton
                quaternary
                @click="modelApi.deleteConfig(m.id).then(() => load())"
              >
                <template #icon><LaIcon name="trash" :size="13" /></template>
              </NButton>
            </div>
          </div>
        </div>
      </div>

      <!-- 提示 -->
      <div class="mt-3 text-[12px] text-muted bg-white border border-line rounded-[8px] p-3 leading-5">
        API Key 使用 Fernet 对称加密存储，接口只返回脱敏字符串。业务代码通过统一
        <code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">BaseLLMProvider</code>
        调用，不直接依赖任何厂商 SDK，后续新增厂商只需实现 Provider 并注册。
      </div>
    </template>

    <!-- 添加供应商 -->
    <VModal v-model:show="showProvider" title="添加模型供应商" :width="520">
      <div class="space-y-3">
        <div>
          <div class="text-[12.5px] text-muted mb-1">供应商类型</div>
          <NSelect
            :value="providerForm.provider_type"
            :options="presetOptions.map((p) => ({ label: p.label, value: p.value }))"
            @update:value="onPresetChange"
          />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">名称</div>
          <NInput v-model:value="providerForm.name" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">API Base URL</div>
          <NInput v-model:value="providerForm.base_url" placeholder="https://api.deepseek.com/v1" />
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">API Key</div>
          <NInput v-model:value="providerForm.api_key" type="password" show-password-on="click" placeholder="sk-..." />
          <div class="text-[11px] text-muted mt-1">密钥将加密存储，不会明文返回前端</div>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-[12.5px] text-ink">设为默认供应商</span>
          <NSwitch v-model:value="providerForm.is_default" :round="false" />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="showProvider = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="createProvider">保存</NButton>
        </div>
      </template>
    </VModal>

    <!-- 添加模型 -->
    <VModal v-model:show="showModel" title="添加模型配置" :width="560">
      <div class="space-y-3">
        <div>
          <div class="text-[12.5px] text-muted mb-1">所属供应商</div>
          <NSelect
            v-model:value="modelForm.provider_id"
            :options="providers.map((p) => ({ label: p.name, value: p.id }))"
          />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div>
            <div class="text-[12.5px] text-muted mb-1">显示名称</div>
            <NInput v-model:value="modelForm.display_name" placeholder="DeepSeek Chat" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">模型名（API 参数）</div>
            <NInput v-model:value="modelForm.model_name" placeholder="deepseek-chat" />
          </div>
        </div>
        <div>
          <div class="text-[12.5px] text-muted mb-1">模型类型</div>
          <NSelect
            v-model:value="modelForm.model_type"
            :options="[
              { label: 'LLM（对话 / 工具调用）', value: 'llm' },
              { label: 'Embedding（知识库向量化）', value: 'embedding' },
            ]"
          />
        </div>
        <div class="grid grid-cols-3 gap-2">
          <div>
            <div class="text-[12.5px] text-muted mb-1">Temperature</div>
            <NInputNumber v-model:value="modelForm.temperature" :min="0" :max="2" :step="0.1" class="!w-full" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Top P</div>
            <NInputNumber v-model:value="modelForm.top_p" :min="0" :max="1" :step="0.05" class="!w-full" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">Max Tokens</div>
            <NInputNumber v-model:value="modelForm.max_tokens" :min="1" :max="32768" class="!w-full" />
          </div>
        </div>
        <div class="flex items-center gap-6">
          <label class="flex items-center gap-2 text-[12.5px] text-ink">
            <NSwitch v-model:value="modelForm.supports_streaming" :round="false" /> 支持流式
          </label>
          <label class="flex items-center gap-2 text-[12.5px] text-ink">
            <NSwitch v-model:value="modelForm.supports_tool_call" :round="false" /> 支持 Tool Calling
          </label>
          <label class="flex items-center gap-2 text-[12.5px] text-ink">
            <NSwitch v-model:value="modelForm.is_default" :round="false" /> 设为默认
          </label>
        </div>
        <div v-if="modelForm.model_type === 'embedding'" class="text-[11.5px] text-[#C86A00]">
          提示：DeepSeek 目前不提供 Embedding 接口，知识库向量化可配置 OpenAI 兼容的 embedding
          服务（如 text-embedding-3-small 或本地 bge-m3 网关）。
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="showModel = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="createModel">保存</NButton>
        </div>
      </template>
    </VModal>
  </div>
</template>
