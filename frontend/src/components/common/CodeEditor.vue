<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as monaco from 'monaco-editor'
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'

const props = withDefaults(
  defineProps<{
    modelValue: string
    language?: string
    height?: string
    readOnly?: boolean
    placeholder?: string
  }>(),
  { language: 'markdown', height: '260px', readOnly: false, placeholder: '' },
)
const emit = defineEmits<{ (e: 'update:modelValue', v: string): void }>()

const container = ref<HTMLDivElement | null>(null)
let editor: monaco.editor.IStandaloneCodeEditor | null = null
let applying = false

// 仅注册基础 worker，避免引入全部语言服务的打包体积
;(self as any).MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
}

onMounted(() => {
  if (!container.value) return
  editor = monaco.editor.create(container.value, {
    value: props.modelValue || '',
    language: props.language === 'markdown' ? 'markdown' : props.language,
    theme: 'vs',
    readOnly: props.readOnly,
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 13,
    lineHeight: 21,
    scrollBeyondLastLine: false,
    wordWrap: 'on',
    renderLineHighlight: 'none',
    padding: { top: 10, bottom: 10 },
    scrollbar: { verticalScrollbarSize: 8, horizontalScrollbarSize: 8 },
    placeholder: props.placeholder,
  })
  editor.onDidChangeModelContent(() => {
    if (applying) return
    emit('update:modelValue', editor?.getValue() ?? '')
  })
})

watch(
  () => props.modelValue,
  (v) => {
    if (!editor) return
    if ((editor.getValue() ?? '') === (v ?? '')) return
    applying = true
    editor.setValue(v ?? '')
    applying = false
  },
)

watch(
  () => props.language,
  (lang) => {
    const model = editor?.getModel()
    if (model) monaco.editor.setModelLanguage(model, lang)
  },
)

onBeforeUnmount(() => editor?.dispose())
</script>

<template>
  <div class="border border-line rounded-lg overflow-hidden bg-white">
    <div ref="container" :style="{ height }"></div>
  </div>
</template>
