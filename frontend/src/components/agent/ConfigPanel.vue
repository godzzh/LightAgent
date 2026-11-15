<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  NButton,
  NInput,
  NInputNumber,
  NSelect,
  NSlider,
  NSwitch,
  NSwitch as NCheck,
  NTag,
  NTooltip,
} from 'naive-ui'
import CodeEditor from '@/components/common/CodeEditor.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import type { AgentConfig, Dataset, ModelConfig, Tool } from '@/types'

const props = defineProps<{
  config: AgentConfig
  models: ModelConfig[]
  tools: Tool[]
  datasets: Dataset[]
  saving: boolean
  dirty: boolean
}>()

const emit = defineEmits<{
  (e: 'update:config', value: AgentConfig): void
  (e: 'save'): void
}>()

const tab = ref<'prompt' | 'model' | 'knowledge' | 'tools' | 'variables'>('prompt')

function patch(partial: Partial<AgentConfig>) {
  emit('update:config', { ...props.config, ...partial } as AgentConfig)
}

const llmOptions = computed(() =>
  props.models.filter((m) => m.model_type === 'llm').map((m) => ({
    label: `${m.display_name} · ${m.model_name}`,
    value: m.id,
  })),
)
const toolOptions = computed(() =>
  props.tools.map((t) => ({
    label: t.name,
    value: t.tool_key,
  })),
)
const datasetOptions = computed(() =>
  props.datasets.map((d) => ({ label: d.name, value: d.id })),
)

const selectedToolKeys = computed({
  get: () => (props.config.tools || []).filter((t) => t.enabled).map((t) => t.tool_key),
  set: (keys: string[]) => patch({ tools: keys.map((k) => ({ tool_key: k, enabled: true })) }),
})

/** 从提示词中自动识别 {{variable}} */
const detectedVars = computed(() => {
  const text = `${props.config.system_prompt || ''}\n${props.config.user_prompt || ''}`
  const found = new Set<string>()
  const re = /\{\{\s*([a-zA-Z0-9_.]+)\s*\}\}/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) found.add(m[1])
  return Array.from(found)
})

const systemVars = computed(() => detectedVars.value.filter((v) => !['query', 'knowledge_context'].includes(v)))

const promptPreview = computed(() => {
  let text = props.config.system_prompt || ''
  text = text.replace(/\{\{\s*knowledge_context\s*\}\}/g, '（此处会注入知识库检索结果）')
  return text
})
</script>

<template>
  <div class="h-full flex flex-col min-h-0">
    <!-- 顶部：iOS 分段控件 -->
    <div class="flex items-center gap-2 px-3 h-[52px] border-b border-line shrink-0">
      <div class="flex items-center gap-0.5 p-[2px] rounded-[6px]" style="background: rgba(118, 118, 128, 0.09)">
        <button
          v-for="t in [
            { k: 'prompt', l: '提示词' },
            { k: 'model', l: '模型' },
            { k: 'knowledge', l: '知识库' },
            { k: 'tools', l: '工具' },
            { k: 'variables', l: '变量' },
          ]"
          :key="t.k"
          class="px-2 h-[26px] rounded-[6px] text-[12px] whitespace-nowrap transition-all duration-200"
          :style="
            tab === t.k
              ? 'background:#fff;color:#1C1C1E;font-weight:600;box-shadow:0 1px 2px rgba(0,0,0,0.10)'
              : 'color:rgba(60,60,67,0.6)'
          "
          @click="tab = t.k as any"
        >
          {{ t.l }}
        </button>
      </div>
      <div class="flex-1"></div>
      <NButton type="primary" :loading="saving" :disabled="!dirty" @click="emit('save')">
        {{ dirty ? '保存' : '已保存' }}
      </NButton>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- 提示词 -->
      <template v-if="tab === 'prompt'">
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-[12.5px] font-medium text-ink">System Prompt</span>
            <NTooltip>
              <template #trigger>
                <span class="text-[11px] text-muted cursor-help flex items-center gap-0.5">
                  <LaIcon name="info" :size="11" /> 支持变量
                </span>
              </template>
              使用 <code v-pre>{{knowledge_context}}</code> 注入知识库内容，
              <code v-pre>{{query}}</code> 表示用户问题
            </NTooltip>
          </div>
          <CodeEditor
            :model-value="config.system_prompt"
            language="markdown"
            height="220px"
            placeholder="你是一名专业的客服助手……"
            @update:model-value="(v: string) => patch({ system_prompt: v })"
          />
        </div>
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">User Prompt 模板</div>
          <NInput
            :value="config.user_prompt"
            type="textarea"
            :rows="2"
            placeholder="{{query}}"
            @update:value="(v: string) => patch({ user_prompt: v })"
          />
        </div>
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">欢迎语</div>
          <NInput
            :value="config.welcome_message"
            type="textarea"
            :rows="2"
            @update:value="(v: string) => patch({ welcome_message: v })"
          />
        </div>
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">开场问题（回车添加）</div>
          <NSelect
            :value="config.opening_questions"
            multiple
            filterable
            tag
            placeholder="例如：如何退换货？"
            :options="(config.opening_questions || []).map((q) => ({ label: q, value: q }))"
            @update:value="(v: string[]) => patch({ opening_questions: v })"
          />
        </div>
        <div class="border border-line rounded-[8px] p-2.5 bg-[#F7F7F9]">
          <div class="text-[11.5px] text-muted mb-1">Prompt 预览（变量已高亮占位）</div>
          <pre class="text-[11.5px] text-[rgba(60,60,67,0.7)] whitespace-pre-wrap break-words font-mono max-h-[140px] overflow-y-auto">{{ promptPreview || '（空）' }}</pre>
        </div>
      </template>

      <!-- 模型 -->
      <template v-if="tab === 'model'">
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">模型</div>
          <NSelect
            :value="config.model_config_id"
            :options="llmOptions"
            placeholder="选择模型"
            @update:value="(v: string) => patch({ model_config_id: v })"
          />
        </div>
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">执行模式</div>
          <NSelect
            :value="config.mode"
            :options="[
              { label: 'Function Calling（推荐，模型原生工具调用）', value: 'function_calling' },
              { label: 'ReAct（文本解析，兼容无工具调用能力的模型）', value: 'react' },
            ]"
            @update:value="(v: any) => patch({ mode: v })"
          />
        </div>
        <div>
          <div class="flex justify-between text-[12.5px] mb-1">
            <span class="font-medium text-ink">Temperature</span>
            <span class="text-muted font-mono">{{ config.temperature }}</span>
          </div>
          <NSlider
            :value="config.temperature"
            :min="0"
            :max="2"
            :step="0.1"
            @update:value="(v: number) => patch({ temperature: v })"
          />
        </div>
        <div>
          <div class="flex justify-between text-[12.5px] mb-1">
            <span class="font-medium text-ink">Top P</span>
            <span class="text-muted font-mono">{{ config.top_p }}</span>
          </div>
          <NSlider
            :value="config.top_p"
            :min="0"
            :max="1"
            :step="0.05"
            @update:value="(v: number) => patch({ top_p: v })"
          />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <div class="text-[12.5px] font-medium text-ink mb-1">最大输出 Token</div>
            <NInputNumber
              :value="config.max_tokens"
              :min="1"
              :max="32768"
              class="!w-full"
              @update:value="(v: number | null) => patch({ max_tokens: v || 2048 })"
            />
          </div>
          <div>
            <div class="text-[12.5px] font-medium text-ink mb-1">最大执行步数</div>
            <NInputNumber
              :value="config.max_steps"
              :min="1"
              :max="30"
              class="!w-full"
              @update:value="(v: number | null) => patch({ max_steps: v || 8 })"
            />
          </div>
        </div>
        <div class="space-y-1.5 pt-1">
          <div class="flex items-center justify-between">
            <span class="text-[12.5px] text-ink">上下文记忆</span>
            <NSwitch
              :value="config.enable_memory"
              :round="false"
              @update:value="(v: boolean) => patch({ enable_memory: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[12.5px] text-ink">启用工具调用</span>
            <NSwitch
              :value="config.enable_tools"
              :round="false"
              @update:value="(v: boolean) => patch({ enable_tools: v })"
            />
          </div>
          <div class="flex items-center justify-between">
            <span class="text-[12.5px] text-ink">启用知识库</span>
            <NSwitch
              :value="config.enable_knowledge"
              :round="false"
              @update:value="(v: boolean) => patch({ enable_knowledge: v })"
            />
          </div>
        </div>
      </template>

      <!-- 知识库 -->
      <template v-if="tab === 'knowledge'">
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">绑定知识库</div>
          <NSelect
            :value="config.dataset_ids"
            multiple
            :options="datasetOptions"
            placeholder="选择要检索的知识库"
            :disabled="!config.enable_knowledge"
            @update:value="(v: string[]) => patch({ dataset_ids: v })"
          />
          <div v-if="!datasetOptions.length" class="text-[11.5px] text-muted mt-1">
            还没有知识库，<RouterLink to="/knowledge" class="text-primary hover:underline">去创建</RouterLink>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-[12.5px] mb-1">
            <span class="font-medium text-ink">Top K</span>
            <span class="text-muted font-mono">{{ config.knowledge_top_k }}</span>
          </div>
          <NSlider
            :value="config.knowledge_top_k"
            :min="1"
            :max="10"
            :step="1"
            @update:value="(v: number) => patch({ knowledge_top_k: v })"
          />
        </div>
        <div>
          <div class="flex justify-between text-[12.5px] mb-1">
            <span class="font-medium text-ink">相似度阈值</span>
            <span class="text-muted font-mono">{{ config.knowledge_threshold }}</span>
          </div>
          <NSlider
            :value="config.knowledge_threshold"
            :min="0"
            :max="1"
            :step="0.05"
            @update:value="(v: number) => patch({ knowledge_threshold: v })"
          />
        </div>
        <div class="text-[11.5px] text-muted bg-[#F7F7F9] border border-line rounded-[8px] p-2.5 leading-5">
          检索流程：用户提问 → 向量化 → 在所选知识库中召回 Top K 片段 → 注入
          <code v-pre>{{knowledge_context}}</code> → 交由模型生成回答并标注来源。
        </div>
      </template>

      <!-- 工具 -->
      <template v-if="tab === 'tools'">
        <div>
          <div class="text-[12.5px] font-medium text-ink mb-1">可用工具</div>
          <NSelect
            v-model:value="selectedToolKeys"
            multiple
            :options="toolOptions"
            placeholder="选择该 Agent 可调用的工具"
            :disabled="!config.enable_tools"
          />
        </div>
        <div v-if="config.tools?.length" class="space-y-1.5">
          <div
            v-for="k in selectedToolKeys"
            :key="k"
            class="flex items-center gap-2 border border-line rounded-[8px] px-2.5 py-2"
          >
            <LaIcon name="tool" :size="13" class="text-primary" />
            <div class="min-w-0 flex-1">
              <div class="text-[12.5px] text-ink">{{ tools.find((t) => t.tool_key === k)?.name || k }}</div>
              <div class="text-[11px] text-muted truncate">
                {{ tools.find((t) => t.tool_key === k)?.description }}
              </div>
            </div>
            <NTag :bordered="false" type="info">{{ k }}</NTag>
          </div>
        </div>
        <div v-else class="text-[12px] text-muted py-4 text-center border border-dashed border-line rounded-[6px]">
          未选择工具。Function Calling 模式下将不会向模型暴露任何函数。
          <div class="mt-1">
            <RouterLink to="/tools" class="text-primary hover:underline">前往工具管理</RouterLink>
          </div>
        </div>
        <div class="text-[11.5px] text-muted bg-[rgba(255,149,0,0.12)] border border-[#FDE68A] rounded-[6px] p-2.5 leading-5">
          工具返回内容视为不可信输入，不会提升为系统指令；每次调用均受超时与最大调用次数限制。
        </div>
      </template>

      <!-- 变量 -->
      <template v-if="tab === 'variables'">
        <div class="text-[11.5px] text-muted leading-5">
          自动从提示词中识别到的变量（保留名 query / knowledge_context 由系统注入）：
        </div>
        <div class="flex flex-wrap gap-1.5">
          <NTag v-for="v in detectedVars" :key="v" :bordered="false" type="info">{{ v }}</NTag>
          <span v-if="!detectedVars.length" class="text-[12px] text-muted">未检测到变量</span>
        </div>
        <div class="pt-2 space-y-2">
          <div class="text-[12.5px] font-medium text-ink">自定义变量</div>
          <div v-if="!config.variables?.length" class="text-[12px] text-muted">暂无自定义变量</div>
          <div
            v-for="(v, i) in config.variables"
            :key="i"
            class="flex items-center gap-2 border border-line rounded-[8px] p-2"
          >
            <NInput
              :value="v.name"
              placeholder="变量名"
              class="!w-[110px]"
              @update:value="(val: string) => {
                const list = [...(config.variables || [])]
                list[i] = { ...list[i], name: val }
                patch({ variables: list })
              }"
            />
            <NInput
              :value="String(v.default ?? '')"
              placeholder="默认值"
              @update:value="(val: string) => {
                const list = [...(config.variables || [])]
                list[i] = { ...list[i], default: val }
                patch({ variables: list })
              }"
            />
            <NButton
              quaternary
              @click="patch({ variables: (config.variables || []).filter((_, idx) => idx !== i) })"
            >
              <template #icon><LaIcon name="trash" :size="13" /></template>
            </NButton>
          </div>
          <NButton
            dashed
            block
            @click="patch({ variables: [...(config.variables || []), { name: '', type: 'string', default: '', description: '' }] })"
          >
            <template #icon><LaIcon name="plus" :size="13" /></template>
            添加变量
          </NButton>
        </div>
      </template>
    </div>
  </div>
</template>
