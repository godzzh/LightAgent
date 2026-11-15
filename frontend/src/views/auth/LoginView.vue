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
  <div class="auth-shell">
    <!-- 背景层：网格 / 光晕 / 扫描线（纯装饰，不参与交互） -->
    <div class="auth-bg" aria-hidden="true">
      <div class="auth-bg__grid"></div>
      <div class="auth-bg__glow auth-bg__glow--a"></div>
      <div class="auth-bg__glow auth-bg__glow--b"></div>
      <div class="auth-bg__scan"></div>
      <div class="auth-bg__noise"></div>
    </div>

    <!-- 顶部系统状态条 -->
    <header class="auth-topbar">
      <div class="auth-brand-mark">
        <span class="auth-brand-mark__core"><LaIcon name="sparkles" :size="18" /></span>
        <span class="auth-brand-mark__text">LIGHTAGENT</span>
        <span class="auth-brand-mark__ver">v0.1</span>
      </div>
      <div class="auth-status" aria-hidden="true">
        <span class="auth-status__dot"></span>
        <span>SYSTEM ONLINE</span>
        <span class="auth-status__sep">/</span>
        <span>SECURE GATEWAY</span>
      </div>
    </header>

    <!-- 主体：左品牌展示 / 右认证面板 -->
    <main class="auth-main">
      <!-- 左侧 HUD 展示区 -->
      <section class="auth-showcase" aria-label="平台介绍">
        <div class="auth-showcase__eyebrow">
          <span class="auth-tick"></span>
          AI AGENT ORCHESTRATION PLATFORM
        </div>
        <h1 class="auth-showcase__title">
          构建<span class="auth-showcase__accent">智能体</span><br />
          的下一<span class="auth-showcase__accent">代工作台</span>
        </h1>
        <p class="auth-showcase__desc">
          可视化编排 Agent、知识库与工作流，把应用发布为 API。<br />
          从提示词到生产级服务，一处完成。
        </p>

        <!-- 装饰性技术刻度 -->
        <div class="auth-hud" aria-hidden="true">
          <div class="auth-hud__row">
            <span class="auth-hud__label">RUNTIME</span>
            <span class="auth-hud__line"></span>
            <span class="auth-hud__value">READY</span>
          </div>
          <div class="auth-hud__row">
            <span class="auth-hud__label">ENGINE</span>
            <span class="auth-hud__line"></span>
            <span class="auth-hud__value">FUNCTION CALLING / REACT</span>
          </div>
          <div class="auth-hud__row">
            <span class="auth-hud__label">MODULES</span>
            <span class="auth-hud__line"></span>
            <span class="auth-hud__value">AGENT · RAG · DAG · API</span>
          </div>
        </div>

        <div class="auth-showcase__footer" aria-hidden="true">
          <span>01 — CONFIGURE</span>
          <span>02 — ORCHESTRATE</span>
          <span>03 — PUBLISH</span>
        </div>
      </section>

      <!-- 右侧认证面板 -->
      <section class="auth-panel-wrap" aria-label="账号认证">
        <div class="auth-panel">
          <!-- 四角装饰括号 -->
          <span class="auth-corner auth-corner--tl" aria-hidden="true"></span>
          <span class="auth-corner auth-corner--tr" aria-hidden="true"></span>
          <span class="auth-corner auth-corner--bl" aria-hidden="true"></span>
          <span class="auth-corner auth-corner--br" aria-hidden="true"></span>

          <div class="auth-panel__head">
            <div class="auth-panel__badge">
              <LaIcon name="shield" :size="14" />
              <span>IDENTITY VERIFICATION</span>
            </div>
            <h2 class="auth-panel__title">{{ mode === 'login' ? '接入工作台' : '创建接入凭证' }}</h2>
            <p class="auth-panel__subtitle">
              {{ mode === 'login' ? '请验证身份以继续访问控制台' : '注册后将自动初始化独立工作空间' }}
            </p>
          </div>

          <NForm ref="formRef" :model="form" :rules="rules" :show-label="false" @keyup.enter="submit">
            <template v-if="mode === 'register'">
              <div class="auth-field">
                <label class="auth-label" for="reg-username">USERNAME</label>
                <NInput v-model:value="form.username" placeholder="用户名（2-32 位）" size="large" input-id="reg-username">
                  <template #prefix><LaIcon name="user" :size="16" class="auth-input-icon" /></template>
                </NInput>
              </div>
              <div class="auth-field">
                <label class="auth-label" for="reg-email">EMAIL</label>
                <NInput v-model:value="form.email" placeholder="邮箱" size="large" input-id="reg-email">
                  <template #prefix><LaIcon name="message" :size="16" class="auth-input-icon" /></template>
                </NInput>
              </div>
            </template>

            <div v-else class="auth-field">
              <label class="auth-label" for="login-account">ACCOUNT</label>
              <NInput v-model:value="form.account" placeholder="用户名或邮箱" size="large" input-id="login-account">
                <template #prefix><LaIcon name="user" :size="16" class="auth-input-icon" /></template>
              </NInput>
            </div>

            <div class="auth-field">
              <label class="auth-label" for="login-password">PASSWORD</label>
              <NInput
                v-model:value="form.password"
                type="password"
                show-password-on="click"
                :placeholder="mode === 'login' ? '密码' : '密码（至少 6 位）'"
                size="large"
                input-id="login-password"
              >
                <template #prefix><LaIcon name="key" :size="16" class="auth-input-icon" /></template>
              </NInput>
            </div>

            <NButton
              type="primary"
              size="large"
              block
              :loading="loading"
              class="auth-submit"
              @click="submit"
            >
              <span v-if="!loading" class="auth-submit__inner">
                {{ mode === 'login' ? '验证并接入' : '注册并接入' }}
                <LaIcon name="chevronRight" :size="16" />
              </span>
              <span v-else>验证中…</span>
            </NButton>
          </NForm>

          <div class="auth-switch">
            {{ mode === 'login' ? '尚无凭证？' : '已有凭证？' }}
            <button
              type="button"
              class="auth-switch__btn"
              @click="mode = mode === 'login' ? 'register' : 'login'"
            >
              {{ mode === 'login' ? '申请接入' : '返回验证' }}
            </button>
          </div>

          <div v-if="mode === 'login'" class="auth-hint" role="note">
            <span class="auth-hint__tag">DEFAULT</span>
            <span>初始管理员凭证</span>
            <code>admin / admin123</code>
          </div>
        </div>

        <p class="auth-footnote">FASTAPI · VUE 3 · POSTGRESQL · PGVECTOR</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
/* ============================================================
   LightAgent Auth · HUD / Sci-Fi FUI（ui-ux-pro-max）
   深色仅作用于登录页；强调色沿用品牌 #184CFF
   ============================================================ */
.auth-shell {
  --auth-accent: #184cff;
  --auth-accent-soft: #6b8cff;
  --auth-bg: #060b18;
  --auth-surface: rgba(12, 20, 38, 0.78);
  --auth-line: rgba(120, 160, 255, 0.16);
  --auth-line-strong: rgba(120, 160, 255, 0.34);
  --auth-text: #eef3ff;
  --auth-text-2: #9fb0d0;
  --auth-text-3: #6b7fa6;
  --auth-mono: 'SFMono-Regular', 'JetBrains Mono', Consolas, 'Liberation Mono', monospace;

  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  flex-direction: column;
  overflow: auto;
  color: var(--auth-text);
  background: var(--auth-bg);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ---------- 背景 ---------- */
.auth-bg { position: fixed; inset: 0; pointer-events: none; overflow: hidden; }
.auth-bg__grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(90, 130, 220, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(90, 130, 220, 0.055) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 90% 80% at 50% 45%, #000 25%, transparent 100%);
}
.auth-bg__glow { position: absolute; border-radius: 50%; filter: blur(90px); }
.auth-bg__glow--a {
  top: -18%; left: 8%; width: 620px; height: 620px;
  background: radial-gradient(circle, rgba(24, 76, 255, 0.28), transparent 68%);
}
.auth-bg__glow--b {
  bottom: -25%; right: -5%; width: 680px; height: 680px;
  background: radial-gradient(circle, rgba(60, 110, 255, 0.2), transparent 68%);
}
.auth-bg__scan {
  position: absolute; inset: 0;
  background: repeating-linear-gradient(180deg, transparent 0 3px, rgba(120, 160, 255, 0.02) 3px 4px);
}
.auth-bg__noise {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.25) 100%);
}
/* 单个缓慢扫描光带（skill: 每屏只动 1-2 个关键元素） */
.auth-bg::after {
  content: '';
  position: absolute;
  left: 0; right: 0; top: 0;
  height: 180px;
  background: linear-gradient(180deg, transparent, rgba(24, 76, 255, 0.07) 60%, rgba(120, 180, 255, 0.14) 98%, transparent);
  animation: auth-scan 9s linear infinite;
}
@keyframes auth-scan { 0% { transform: translateY(-200px); } 100% { transform: translateY(100vh); } }

/* ---------- 顶部状态条 ---------- */
.auth-topbar {
  position: relative; z-index: 2;
  display: flex; align-items: center; justify-content: space-between;
  height: 64px; padding: 0 40px; flex: none;
  border-bottom: 1px solid var(--auth-line);
  background: rgba(6, 11, 24, 0.6);
  backdrop-filter: blur(12px);
}
.auth-brand-mark { display: flex; align-items: center; gap: 10px; }
.auth-brand-mark__core {
  display: grid; place-items: center; width: 30px; height: 30px;
  color: #fff; border-radius: 4px;
  background: linear-gradient(145deg, var(--auth-accent-soft), var(--auth-accent));
  box-shadow: 0 0 18px rgba(24, 76, 255, 0.45);
}
.auth-brand-mark__text { font-family: var(--auth-mono); font-size: 13px; font-weight: 700; letter-spacing: 0.18em; }
.auth-brand-mark__ver { font-family: var(--auth-mono); font-size: 10px; color: var(--auth-text-3); border: 1px solid var(--auth-line); padding: 2px 6px; border-radius: 3px; }
.auth-status { display: flex; align-items: center; gap: 10px; font-family: var(--auth-mono); font-size: 10.5px; letter-spacing: 0.12em; color: var(--auth-text-3); }
.auth-status__dot { width: 6px; height: 6px; border-radius: 50%; background: #34d399; box-shadow: 0 0 8px #34d399; }
.auth-status__sep { opacity: 0.5; }

/* ---------- 主体分栏 ---------- */
.auth-main {
  position: relative; z-index: 2;
  flex: 1; min-height: 0;
  display: grid; grid-template-columns: minmax(0, 1fr) 460px;
  gap: 60px; align-items: center;
  max-width: 1320px; width: 100%; margin: 0 auto;
  padding: 40px 48px;
}

/* ---------- 左侧展示 ---------- */
.auth-showcase { min-width: 0; }
.auth-showcase__eyebrow {
  display: inline-flex; align-items: center; gap: 10px;
  font-family: var(--auth-mono); font-size: 11px; letter-spacing: 0.2em;
  color: var(--auth-accent-soft); text-transform: uppercase;
  padding: 7px 12px; border: 1px solid var(--auth-line-strong); border-radius: 3px;
  background: rgba(24, 76, 255, 0.07);
}
.auth-tick { width: 14px; height: 1px; background: var(--auth-accent-soft); box-shadow: 0 0 6px var(--auth-accent); }
.auth-showcase__title {
  margin: 28px 0 0;
  font-size: clamp(34px, 4.2vw, 58px); font-weight: 700; line-height: 1.22;
  letter-spacing: -0.02em; color: #f4f7ff;
  text-shadow: 0 0 40px rgba(24, 76, 255, 0.18);
}
.auth-showcase__accent {
  background: linear-gradient(100deg, #7aa2ff, #184cff 60%, #8ab4ff);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.auth-showcase__desc { margin: 22px 0 0; font-size: 14.5px; line-height: 1.9; color: var(--auth-text-2); }

.auth-hud { margin-top: 44px; max-width: 460px; border-top: 1px solid var(--auth-line); }
.auth-hud__row { display: flex; align-items: center; gap: 14px; height: 44px; border-bottom: 1px solid var(--auth-line); font-family: var(--auth-mono); font-size: 10.5px; letter-spacing: 0.1em; }
.auth-hud__label { color: var(--auth-text-3); width: 78px; flex: none; }
.auth-hud__line { flex: 1; height: 1px; background: repeating-linear-gradient(90deg, var(--auth-line-strong) 0 4px, transparent 4px 9px); }
.auth-hud__value { color: var(--auth-text-2); white-space: nowrap; }
.auth-showcase__footer { display: flex; gap: 26px; margin-top: 40px; font-family: var(--auth-mono); font-size: 10px; letter-spacing: 0.14em; color: var(--auth-text-3); }

/* ---------- 右侧面板 ---------- */
.auth-panel-wrap { display: flex; flex-direction: column; align-items: center; gap: 18px; min-width: 0; }
.auth-panel {
  position: relative; width: 100%;
  padding: 34px 32px 30px;
  background: var(--auth-surface);
  border: 1px solid var(--auth-line-strong);
  border-radius: 8px;
  box-shadow: 0 24px 80px rgba(0, 8, 30, 0.6), inset 0 1px 0 rgba(255,255,255,0.04), 0 0 40px rgba(24, 76, 255, 0.08);
  backdrop-filter: blur(20px);
}
/* 四角 HUD 括号 */
.auth-corner { position: absolute; width: 16px; height: 16px; pointer-events: none; }
.auth-corner--tl { top: -1px; left: -1px; border-top: 2px solid var(--auth-accent); border-left: 2px solid var(--auth-accent); }
.auth-corner--tr { top: -1px; right: -1px; border-top: 2px solid var(--auth-accent); border-right: 2px solid var(--auth-accent); }
.auth-corner--bl { bottom: -1px; left: -1px; border-bottom: 2px solid var(--auth-accent); border-left: 2px solid var(--auth-accent); }
.auth-corner--br { bottom: -1px; right: -1px; border-bottom: 2px solid var(--auth-accent); border-right: 2px solid var(--auth-accent); }

.auth-panel__head { margin-bottom: 26px; }
.auth-panel__badge { display: inline-flex; align-items: center; gap: 7px; font-family: var(--auth-mono); font-size: 10px; letter-spacing: 0.16em; color: var(--auth-accent-soft); }
.auth-panel__title { margin: 14px 0 0; font-size: 24px; font-weight: 650; letter-spacing: -0.01em; color: #f4f7ff; }
.auth-panel__subtitle { margin: 7px 0 0; font-size: 12.5px; color: var(--auth-text-3); }

/* 字段 */
.auth-field { margin-bottom: 18px; }
.auth-label { display: block; margin-bottom: 8px; font-family: var(--auth-mono); font-size: 10px; letter-spacing: 0.18em; color: var(--auth-text-3); }
.auth-input-icon { color: var(--auth-text-3); }

/* 深度覆盖 naive-ui 输入：深色 HUD 风格（naive-ui 组件仍为 4px 圆角） */
.auth-panel :deep(.n-input) {
  background: rgba(6, 12, 28, 0.7) !important;
  border-radius: 4px !important;
  --n-border: 1px solid var(--auth-line-strong) !important;
  --n-border-hover: 1px solid rgba(24, 76, 255, 0.7) !important;
  --n-border-focus: 1px solid var(--auth-accent) !important;
  --n-box-shadow-focus: 0 0 0 3px rgba(24, 76, 255, 0.22) !important;
  --n-color: rgba(6, 12, 28, 0.7) !important;
  --n-text-color: #eef3ff !important;
  --n-placeholder-color: #5f719a !important;
  --n-caret-color: #7aa2ff !important;
  --n-height: 44px !important;
}
.auth-panel :deep(.n-input .n-input__border),
.auth-panel :deep(.n-input .n-input__state-border) { border-radius: 4px !important; }
.auth-panel :deep(.n-input__input-el) { color: #eef3ff !important; }
.auth-panel :deep(.n-input__prefix) { color: var(--auth-text-3) !important; }

/* 提交按钮 */
.auth-submit {
  height: 46px !important; margin-top: 6px;
  font-size: 14.5px !important; font-weight: 600 !important;
  border-radius: 4px !important;
  background: linear-gradient(100deg, #2a5cff, #184cff) !important;
  box-shadow: 0 8px 26px rgba(24, 76, 255, 0.42), inset 0 1px 0 rgba(255,255,255,0.18) !important;
  letter-spacing: 0.04em;
  transition: transform 160ms ease, box-shadow 200ms ease, filter 200ms ease !important;
}
.auth-submit:hover { filter: brightness(1.12); box-shadow: 0 10px 34px rgba(24, 76, 255, 0.58) !important; }
.auth-submit:active { transform: scale(0.985); }
.auth-submit__inner { display: inline-flex; align-items: center; justify-content: center; gap: 8px; }

/* 切换 / 提示 */
.auth-switch { margin-top: 20px; text-align: center; font-size: 12.5px; color: var(--auth-text-3); }
.auth-switch__btn { margin-left: 4px; padding: 2px 4px; color: #8aa8ff; font-weight: 600; background: none; border: 0; border-radius: 3px; cursor: pointer; transition: color 160ms ease, background-color 160ms ease; }
.auth-switch__btn:hover { color: #b9ccff; background: rgba(24, 76, 255, 0.12); }
.auth-switch__btn:focus-visible { outline: 2px solid var(--auth-accent); outline-offset: 2px; }
.auth-hint {
  display: flex; align-items: center; justify-content: center; flex-wrap: wrap; gap: 8px;
  margin-top: 20px; padding: 10px 12px;
  font-size: 11.5px; color: var(--auth-text-3);
  background: rgba(24, 76, 255, 0.06);
  border: 1px dashed var(--auth-line-strong); border-radius: 4px;
}
.auth-hint__tag { font-family: var(--auth-mono); font-size: 9.5px; letter-spacing: 0.1em; color: var(--auth-accent-soft); border: 1px solid var(--auth-line-strong); border-radius: 3px; padding: 2px 6px; }
.auth-hint code { font-family: var(--auth-mono); font-size: 11.5px; color: #cdd9f5; }
.auth-footnote { font-family: var(--auth-mono); font-size: 10px; letter-spacing: 0.14em; color: rgba(107, 127, 166, 0.7); text-align: center; }

/* 入场：仅面板淡入位移（skill: 1-2 个关键动效） */
.auth-panel { animation: auth-enter 520ms cubic-bezier(0.22, 1, 0.36, 1) both; }
@keyframes auth-enter { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }

/* ---------- 响应式 ---------- */
@media (max-width: 1024px) {
  .auth-main { grid-template-columns: 1fr; gap: 32px; padding: 32px 28px; max-width: 560px; }
  .auth-showcase { display: none; }
  .auth-panel-wrap { width: 100%; }
}
@media (max-width: 560px) {
  .auth-topbar { padding: 0 18px; }
  .auth-status { display: none; }
  .auth-main { padding: 24px 16px; }
  .auth-panel { padding: 26px 20px 24px; }
}

/* ---------- 无障碍：减弱动效 ---------- */
@media (prefers-reduced-motion: reduce) {
  .auth-bg::after, .auth-panel { animation: none !important; }
  .auth-submit { transition: none !important; }
}
</style>
