<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { NButton, NInput, NSpin, useMessage } from 'naive-ui'
import PageHeader from '@/components/common/PageHeader.vue'
import LaIcon from '@/components/common/LaIcon.vue'
import { authApi } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const message = useMessage()
const loading = ref(false)
const saving = ref(false)
const form = reactive({ username: '', password: '', confirm: '' })

async function load() {
  loading.value = true
  try {
    await userStore.fetchMe(true)
    form.username = userStore.user?.username || ''
  } finally {
    loading.value = false
  }
}

async function save() {
  if (form.password && form.password !== form.confirm) {
    message.warning('两次输入的密码不一致')
    return
  }
  if (form.password && form.password.length < 6) {
    message.warning('密码至少 6 位')
    return
  }
  saving.value = true
  try {
    await authApi.update({
      username: form.username !== userStore.user?.username ? form.username : undefined,
      password: form.password || undefined,
    })
    message.success('已保存')
    form.password = ''
    form.confirm = ''
    await load()
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="la-page">
    <PageHeader title="系统设置" subtitle="账号、工作空间与平台信息" />

    <div v-if="loading" class="la-card p-10 flex justify-center"><NSpin /></div>

    <template v-else>
      <div class="la-card p-5 mb-3">
        <div class="text-[14px] font-medium text-ink mb-3">账号信息</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div>
            <div class="text-[12.5px] text-muted mb-1">用户名</div>
            <NInput v-model:value="form.username" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">邮箱</div>
            <NInput :value="userStore.user?.email" disabled />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">新密码（留空不修改）</div>
            <NInput v-model:value="form.password" type="password" show-password-on="click" />
          </div>
          <div>
            <div class="text-[12.5px] text-muted mb-1">确认新密码</div>
            <NInput v-model:value="form.confirm" type="password" show-password-on="click" />
          </div>
        </div>
        <div class="mt-4">
          <NButton type="primary" :loading="saving" @click="save">保存修改</NButton>
        </div>
      </div>

      <div class="la-card p-5 mb-3">
        <div class="text-[14px] font-medium text-ink mb-3">工作空间</div>
        <div class="flex items-center gap-3">
          <span class="w-9 h-9 rounded-[6px] bg-[rgba(24,76,255,0.11)] text-primary flex items-center justify-center">
            <LaIcon name="dashboard" :size="17" />
          </span>
          <div>
            <div class="text-[13px] text-ink">{{ userStore.workspace?.name }}</div>
            <div class="text-[11.5px] text-muted">{{ userStore.workspace?.description || '默认工作空间' }}</div>
          </div>
        </div>
      </div>

      <div class="la-card p-5">
        <div class="text-[14px] font-medium text-ink mb-3">平台信息</div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12.5px]">
          <div class="border border-line rounded-[8px] p-3">
            <div class="text-[11.5px] text-muted">前端</div>
            <div class="text-ink mt-0.5">Vue 3 + TypeScript + Vite + Naive UI + Tailwind</div>
          </div>
          <div class="border border-line rounded-[8px] p-3">
            <div class="text-[11.5px] text-muted">后端</div>
            <div class="text-ink mt-0.5">FastAPI + SQLAlchemy 2.x + PostgreSQL/pgvector</div>
          </div>
          <div class="border border-line rounded-[8px] p-3">
            <div class="text-[11.5px] text-muted">接口文档</div>
            <a href="/docs" target="_blank" class="text-primary hover:underline mt-0.5 inline-flex items-center gap-1">
              Swagger / OpenAPI <LaIcon name="external" :size="11" />
            </a>
          </div>
          <div class="border border-line rounded-[8px] p-3">
            <div class="text-[11.5px] text-muted">健康检查</div>
            <a href="/health" target="_blank" class="text-primary hover:underline mt-0.5 inline-flex items-center gap-1">
              /health <LaIcon name="external" :size="11" />
            </a>
          </div>
        </div>
        <div class="text-[11.5px] text-muted mt-3 leading-5">
          安全提示：API Key 加密存储、HTTP 工具执行前做 SSRF 校验、Code 节点使用受限表达式求值，
          平台不会在日志中记录明文密钥。
        </div>
      </div>
    </template>
  </div>
</template>
