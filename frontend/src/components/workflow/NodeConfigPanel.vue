<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NDropdown, NInput, NInputNumber, NSelect, NSlider, NTag, useMessage } from 'naive-ui'
import LaIcon from '@/components/common/LaIcon.vue'
import type { Dataset, ModelConfig } from '@/types'

const props = defineProps<{
  nodeId: string
  nodeType: string
  data: Record<string, any>
  upstreamVars: { label: string; value: string }[]
  models: ModelConfig[]
  datasets: Dataset[]
}>()

const emit = defineEmits<{ (e: 'update', data: Record<string, any>): void }>()
const message = useMessage()

function patch(partial: Record<string, any>) {
  emit('update', { ...props.data, ...partial })
}

const llmOptions = computed(() =>
  props.models.filter((m) => m.model_type === 'llm').map((m) => ({ label: `${m.display_name}`, value: m.id })),
)
const datasetOptions = computed(() => props.datasets.map((d) => ({ label: d.name, value: d.id })))
const varOptions = computed(() =>
  props.upstreamVars.length
    ? props.upstreamVars.map((v) => ({ label: v.label, value: v.value }))
    : [{ label: '暂无上游变量', value: '', disabled: true }],
)

const typeLabel: Record<string, string> = {
  start: '开始节点',
  llm: '大模型节点',
  knowledge: '知识检索节点',
  http: 'HTTP 请求节点',
  code: '代码节点',
  condition: '条件分支节点',
  variable: '变量赋值节点',
  answer: '输出节点',
  end: '结束节点',
}

function addParam() {
  patch({ params: [...(props.data.params || []), { name: '', type: 'string', required: true, default: '', description: '' }] })
}

/** 变量选择：把 {{path}} 追加到目标字段 */
function appendVar(field: string, value: string) {
  if (!value) return
  patch({ [field]: `${props.data[field] || ''}{{${value}}}` })
  message.success(`已插入 {{${value}}}`)
}

function parseJson(text: string, field: string) {
  try {
    patch({ [field]: text ? JSON.parse(text) : {} })
  } catch {
    /* 输入过程中允许非法 JSON，只在保存/运行时报错 */
  }
}

const headersText = computed(() => JSON.stringify(props.data.headers || {}, null, 0))
const paramsText = computed(() => JSON.stringify(props.data.params_obj || {}, null, 0))
</script>

<template>
  <div class="h-full flex flex-col min-h-0">
    <div class="h-10 px-3 flex items-center justify-between border-b border-line shrink-0">
      <div class="flex items-center gap-1.5 min-w-0">
        <span class="text-[12.5px] font-medium text-ink truncate">{{ typeLabel[nodeType] || nodeType }}</span>
        <NTag size="tiny" :bordered="false">{{ nodeId }}</NTag>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto p-3 space-y-3 text-[12.5px]">
      <!-- START -->
      <template v-if="nodeType === 'start'">
        <div class="text-[11.5px] text-muted">定义工作流输入参数，运行时逐项填值。</div>
        <div v-for="(p, i) in data.params || []" :key="i" class="border border-line rounded-lg p-2 space-y-1.5">
          <div class="flex items-center gap-1.5">
            <NInput
              :value="p.name"
              size="tiny"
              placeholder="参数名"
              @update:value="(v: string) => {
                const list = [...(data.params || [])]
                list[i] = { ...list[i], name: v }
                patch({ params: list })
              }"
            />
            <NSelect
              :value="p.type"
              size="tiny"
              class="!w-[86px]"
              :options="['string', 'number', 'boolean'].map((t) => ({ label: t, value: t }))"
              @update:value="(v: string) => {
                const list = [...(data.params || [])]
                list[i] = { ...list[i], type: v }
                patch({ params: list })
              }"
            />
            <NButton size="tiny" quaternary @click="patch({ params: (data.params || []).filter((_: any, j: number) => j !== i) })">
              <template #icon><LaIcon name="close" :size="12" /></template>
            </NButton>
          </div>
          <NInput
            :value="String(p.default ?? '')"
            size="tiny"
            placeholder="默认值"
            @update:value="(v: string) => {
              const list = [...(data.params || [])]
              list[i] = { ...list[i], default: v }
              patch({ params: list })
            }"
          />
          <NInput
            :value="p.description || ''"
            size="tiny"
            placeholder="参数说明"
            @update:value="(v: string) => {
              const list = [...(data.params || [])]
              list[i] = { ...list[i], description: v }
              patch({ params: list })
            }"
          />
        </div>
        <NButton size="tiny" dashed block @click="addParam">
          <template #icon><LaIcon name="plus" :size="12" /></template>
          添加输入参数
        </NButton>
      </template>

      <!-- LLM -->
      <template v-if="nodeType === 'llm'">
        <div>
          <div class="text-muted mb-1">模型</div>
          <NSelect
            :value="data.model_config_id"
            :options="llmOptions"
            placeholder="选择模型（默认使用系统默认模型）"
            clearable
            size="small"
            @update:value="(v: string) => patch({ model_config_id: v })"
          />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-muted">System Prompt</span>
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => appendVar('system_prompt', v)">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                变量
              </NButton>
            </NDropdown>
          </div>
          <NInput :value="data.system_prompt" type="textarea" :rows="3" placeholder="你是一名助手……" @update:value="(v: string) => patch({ system_prompt: v })" />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-muted">User Prompt</span>
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => appendVar('user_prompt', v)">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                变量
              </NButton>
            </NDropdown>
          </div>
          <NInput :value="data.user_prompt" type="textarea" :rows="4" placeholder="根据 {{start.query}} 回答" @update:value="(v: string) => patch({ user_prompt: v })" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <div class="text-muted mb-1">Temperature</div>
            <NSlider :value="data.temperature ?? 0.7" :min="0" :max="2" :step="0.1" @update:value="(v: number) => patch({ temperature: v })" />
          </div>
          <div>
            <div class="text-muted mb-1">Max Tokens</div>
            <NInputNumber :value="data.max_tokens ?? 2048" :min="1" :max="8192" size="tiny" class="!w-full" @update:value="(v: number | null) => patch({ max_tokens: v || 2048 })" />
          </div>
        </div>
      </template>

      <!-- KNOWLEDGE -->
      <template v-if="nodeType === 'knowledge'">
        <div>
          <div class="text-muted mb-1">知识库</div>
          <NSelect
            :value="data.dataset_ids || []"
            multiple
            :options="datasetOptions"
            placeholder="选择知识库"
            size="small"
            @update:value="(v: string[]) => patch({ dataset_ids: v })"
          />
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-muted">检索问题</span>
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => appendVar('query', v)">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                变量
              </NButton>
            </NDropdown>
          </div>
          <NInput :value="data.query" type="textarea" :rows="2" placeholder="例如 {{start.query}}" @update:value="(v: string) => patch({ query: v })" />
        </div>
        <div class="grid grid-cols-2 gap-2">
          <div>
            <div class="text-muted mb-1">Top K</div>
            <NInputNumber :value="data.top_k ?? 4" :min="1" :max="20" size="tiny" class="!w-full" @update:value="(v: number | null) => patch({ top_k: v || 4 })" />
          </div>
          <div>
            <div class="text-muted mb-1">阈值</div>
            <NInputNumber :value="data.threshold ?? 0.3" :min="0" :max="1" :step="0.05" size="tiny" class="!w-full" @update:value="(v: number | null) => patch({ threshold: v ?? 0.3 })" />
          </div>
        </div>
      </template>

      <!-- HTTP -->
      <template v-if="nodeType === 'http'">
        <div class="grid grid-cols-[1fr_92px] gap-2">
          <div>
            <div class="text-muted mb-1">URL</div>
            <NInput :value="data.url" size="small" placeholder="https://api.example.com/x" @update:value="(v: string) => patch({ url: v })" />
          </div>
          <div>
            <div class="text-muted mb-1">Method</div>
            <NSelect :value="data.method || 'GET'" size="small" :options="['GET', 'POST', 'PUT', 'DELETE'].map((m) => ({ label: m, value: m }))" @update:value="(v: string) => patch({ method: v })" />
          </div>
        </div>
        <div>
          <div class="text-muted mb-1">Headers（JSON）</div>
          <NInput :value="headersText" type="textarea" :rows="2" class="font-mono" @update:value="(v: string) => parseJson(v, 'headers')" />
        </div>
        <div>
          <div class="text-muted mb-1">Query 参数（JSON）</div>
          <NInput :value="paramsText" type="textarea" :rows="2" class="font-mono" @update:value="(v: string) => parseJson(v, 'params_obj')" />
        </div>
        <div>
          <div class="text-muted mb-1">Body（JSON）</div>
          <NInput :value="typeof data.body === 'string' ? data.body : JSON.stringify(data.body || '', null, 2)" type="textarea" :rows="3" class="font-mono" @update:value="(v: string) => parseJson(v, 'body')" />
        </div>
        <div>
          <div class="text-muted mb-1">超时（秒）</div>
          <NInputNumber :value="data.timeout ?? 20" :min="1" :max="120" size="tiny" class="!w-full" @update:value="(v: number | null) => patch({ timeout: v || 20 })" />
        </div>
      </template>

      <!-- CODE -->
      <template v-if="nodeType === 'code'">
        <div class="text-[11.5px] text-muted leading-5">
          受限表达式求值（不使用 eval），支持变量下标、算术、比较与 len/str/int/join 等内置函数。
          例：<code class="bg-[rgba(118,118,128,0.08)] px-1 rounded">llm_1.text[:100]</code>
        </div>
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-muted">表达式</span>
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => appendVar('expression', v)">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                变量
              </NButton>
            </NDropdown>
          </div>
          <NInput :value="data.expression" type="textarea" :rows="4" class="font-mono" placeholder="llm_1.text" @update:value="(v: string) => patch({ expression: v })" />
        </div>
        <div>
          <div class="text-muted mb-1">输出变量名</div>
          <NInput :value="data.output_key || 'result'" size="small" @update:value="(v: string) => patch({ output_key: v })" />
        </div>
      </template>

      <!-- CONDITION -->
      <template v-if="nodeType === 'condition'">
        <div>
          <div class="text-muted mb-1">左值</div>
          <NInput :value="data.left" size="small" placeholder="{{llm_1.text}}" @update:value="(v: string) => patch({ left: v })" />
          <div class="mt-1">
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => patch({ left: `{{${v}}}` })">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                选择变量
              </NButton>
            </NDropdown>
          </div>
        </div>
        <div>
          <div class="text-muted mb-1">运算符</div>
          <NSelect
            :value="data.operator || 'eq'"
            size="small"
            :options="[
              { label: '等于', value: 'eq' },
              { label: '不等于', value: 'ne' },
              { label: '大于', value: 'gt' },
              { label: '大于等于', value: 'gte' },
              { label: '小于', value: 'lt' },
              { label: '小于等于', value: 'lte' },
              { label: '包含', value: 'contains' },
              { label: '不包含', value: 'not_contains' },
              { label: '为空', value: 'empty' },
              { label: '不为空', value: 'not_empty' },
            ]"
            @update:value="(v: string) => patch({ operator: v })"
          />
        </div>
        <div>
          <div class="text-muted mb-1">右值</div>
          <NInput :value="data.right" size="small" placeholder="比较值，可为变量" @update:value="(v: string) => patch({ right: v })" />
        </div>
        <div class="text-[11.5px] text-muted bg-[#F7F7F9] border border-line rounded-lg p-2">
          条件为真走「是」分支，否则走「否」分支。分支连线请在画布上从对应出口拖出。
        </div>
      </template>

      <!-- VARIABLE -->
      <template v-if="nodeType === 'variable'">
        <div>
          <div class="text-muted mb-1">变量名</div>
          <NInput :value="data.name" size="small" @update:value="(v: string) => patch({ name: v })" />
        </div>
        <div>
          <div class="text-muted mb-1">值（支持变量引用）</div>
          <NInput :value="data.value" type="textarea" :rows="2" @update:value="(v: string) => patch({ value: v })" />
        </div>
      </template>

      <!-- ANSWER -->
      <template v-if="nodeType === 'answer'">
        <div>
          <div class="flex items-center justify-between mb-1">
            <span class="text-muted">输出内容模板</span>
            <NDropdown :options="varOptions" trigger="click" @select="(v: string) => appendVar('answer', v)">
              <NButton size="tiny" quaternary>
                <template #icon><LaIcon name="variable" :size="12" /></template>
                变量
              </NButton>
            </NDropdown>
          </div>
          <NInput :value="data.answer" type="textarea" :rows="5" placeholder="{{llm_1.text}}" @update:value="(v: string) => patch({ answer: v })" />
        </div>
      </template>

      <!-- END -->
      <template v-if="nodeType === 'end'">
        <div class="text-[11.5px] text-muted leading-5">
          工作流在此结束，返回输出节点的内容。如需自定义返回结构，请使用「输出」节点。
        </div>
      </template>

      <!-- 上游变量 -->
      <div v-if="upstreamVars.length" class="border-t border-line pt-2">
        <div class="text-[11.5px] text-muted mb-1">可用上游变量</div>
        <div class="flex flex-wrap gap-1">
          <span
            v-for="v in upstreamVars"
            :key="v.value"
            class="text-[10.5px] px-1.5 py-0.5 rounded bg-[rgba(0,122,255,0.09)] text-[#007AFF] font-mono cursor-pointer hover:bg-[rgba(0,122,255,0.12)]"
            :title="v.label"
            @click="appendVar(nodeType === 'llm' ? 'user_prompt' : nodeType === 'answer' ? 'answer' : 'query', v.value)"
          >
            {{ v.value }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
