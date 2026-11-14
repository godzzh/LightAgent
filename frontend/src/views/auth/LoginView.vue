<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NForm, NFormItem, NInput, useMessage, type FormInst, type FormRules } from 'naive-ui'
import LaIcon from '@/components/common/LaIcon.vue'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'
import { setToken } from '@/api/client'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const userStore = useUserStore()

const mode = ref<'login' | 'register'>('login')
const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const form = reactive({ account: 'admin', password: 'admin123', username: '', email: '' })

const rules: FormRules = {
  account: [{ required: true, message: '请输入用户名或邮箱', trigger: ['blur', 'input'] }],
  password: [{ required: true, message: '请输入密码', trigger: ['blur', 'input'] }],
}

async function submit() {
  if (mode.value === 'login') {
    if (!form.account || !form.password) {
      message.warning('请填写账号和密码')
      return
    }
    loading.value = true
    try {
      await userStore.login(form.account, form.password)
      message.success('登录成功')
      const redirect = (route.query.redirect as string) || '/dashboard'
      router.replace(redirect)
    } catch {
      /* 错误提示已由拦截器处理 */
    } finally {
      loading.value = false
    }
    return
  }

  if (!form.username || !form.email || !form.password) {
    message.warning('请完整填写注册信息')
    return
  }
  loading.value = true
  try {
    const res = await authApi.register({
      username: form.username,
      email: form.email,
      password: form.password,
    })
    setToken(res.access_token)
    message.success('注册成功，已自动登录')
    router.replace('/dashboard')
  } catch {
    /* ignore */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen w-full flex flex-col items-center justify-center px-5 py-10 bg-surface relative">
    <!-- 背景柔光，模拟 iOS 壁纸的柔和层次 -->
    <div
      class="pointer-events-none absolute inset-x-0 top-0 h-[420px]"
      style="background: radial-gradient(60% 100% at 50% 0%, rgba(0, 122, 255, 0.14) 0%, rgba(0, 122, 255, 0) 70%)"
    ></div>

    <div class="w-full max-w-[400px] relative la-enter">
      <!-- App 图标 + 标题 -->
      <div class="flex flex-col items-center mb-7">
        <div
          class="w-[62px] h-[62px] rounded-[15px] flex items-center justify-center text-white mb-4"
          style="background: linear-gradient(160deg, #4ba3ff 0%, #007aff 100%); box-shadow: 0 6px 20px -6px rgba(0, 122, 255, 0.6)"
        >
          <LaIcon name="sparkles" :size="30" :stroke-width="2" />
        </div>
        <h1 class="text-[26px] font-bold text-ink tracking-tight">LightAgent</h1>
        <p class="text-[13px] text-muted mt-1">
          {{ mode === 'login' ? '登录你的 AI 应用工作台' : '创建账号，自动初始化工作空间' }}
        </p>
      </div>

      <!-- 表单卡 -->
      <div class="la-card p-6">
        <NForm ref="formRef" :model="form" :rules="rules" :show-label="false" @keyup.enter="submit">
          <template v-if="mode === 'register'">
            <NFormItem path="username">
              <NInput v-model:value="form.username" placeholder="用户名（2-32 位）" size="large">
                <template #prefix><LaIcon name="user" :size="16" class="text-[rgba(60,60,67,0.38)]" /></template>
              </NInput>
            </NFormItem>
            <NFormItem path="email">
              <NInput v-model:value="form.email" placeholder="邮箱" size="large">
                <template #prefix><LaIcon name="message" :size="16" class="text-[rgba(60,60,67,0.38)]" /></template>
              </NInput>
            </NFormItem>
          </template>
          <NFormItem v-else path="account">
            <NInput v-model:value="form.account" placeholder="用户名或邮箱" size="large">
              <template #prefix><LaIcon name="user" :size="16" class="text-[rgba(60,60,67,0.38)]" /></template>
            </NInput>
          </NFormItem>

          <NFormItem path="password">
            <NInput
              v-model:value="form.password"
              type="password"
              show-password-on="click"
              :placeholder="mode === 'login' ? '密码' : '密码（至少 6 位）'"
              size="large"
            >
              <template #prefix><LaIcon name="key" :size="16" class="text-[rgba(60,60,67,0.38)]" /></template>
            </NInput>
          </NFormItem>

          <NButton
            type="primary"
            size="large"
            block
            :loading="loading"
            class="mt-1"
            style="height: 46px; font-size: 15px; font-weight: 600"
            @click="submit"
          >
            {{ mode === 'login' ? '登录' : '注册并登录' }}
          </NButton>
        </NForm>

        <div class="mt-4 text-center text-[13px] text-muted">
          {{ mode === 'login' ? '还没有账号？' : '已有账号？' }}
          <button
            class="text-primary font-medium ml-1 ios-press"
            @click="mode = mode === 'login' ? 'register' : 'login'"
          >
            {{ mode === 'login' ? '立即注册' : '返回登录' }}
          </button>
        </div>
      </div>

      <!-- 初始账号提示 -->
      <div
        v-if="mode === 'login'"
        class="mt-4 text-[12px] text-muted text-center leading-relaxed px-4 py-3 rounded-[14px]"
        style="background: rgba(118, 118, 128, 0.08)"
      >
        首次启动自动创建管理员账号
        <span class="font-mono text-ink font-medium">admin / admin123</span>
        <br />登录后请及时修改密码
      </div>

      <div class="mt-6 text-center text-[11.5px] text-muted opacity-80">
        FastAPI · Vue 3 · PostgreSQL · pgvector
      </div>
    </div>
  </div>
</template>
