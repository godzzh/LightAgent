<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import { NDropdown, NSpin, useMessage } from 'naive-ui'
import LaIcon from '@/components/common/LaIcon.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const userStore = useUserStore()
const booting = ref(true)

/** 导航按职责分组，贴近 iOS 设置页的信息层级 */
const groups = [
  {
    label: '工作台',
    items: [
      { name: 'dashboard', label: '工作空间', icon: 'dashboard' },
      { name: 'applications', label: '应用管理', icon: 'apps' },
      { name: 'workflows', label: '工作流', icon: 'flow' },
    ],
  },
  {
    label: '资源',
    items: [
      { name: 'knowledge', label: '知识库', icon: 'book' },
      { name: 'tools', label: '工具管理', icon: 'tool' },
      { name: 'models', label: '模型管理', icon: 'cpu' },
    ],
  },
  {
    label: '系统',
    items: [
      { name: 'logs', label: '运行日志', icon: 'logs' },
      { name: 'settings', label: '系统设置', icon: 'settings' },
    ],
  },
]

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/applications/')) return 'applications'
  if (path.startsWith('/knowledge/')) return 'knowledge'
  if (path.startsWith('/workflows/')) return 'workflows'
  return (route.name as string) || 'dashboard'
})

const title = computed(() => (route.meta.title as string) || 'LightAgent')

const userOptions = [
  { label: '账号设置', key: 'settings' },
  { label: '退出登录', key: 'logout' },
]

function go(name: string) {
  router.push({ name })
}

function onUserSelect(key: string) {
  if (key === 'logout') {
    userStore.logout()
    message.success('已退出登录')
    router.replace('/login')
  } else if (key === 'settings') {
    router.push('/settings')
  }
}

onMounted(async () => {
  try {
    const u = await userStore.fetchMe()
    if (!u) router.replace('/login')
  } finally {
    booting.value = false
  }
})
</script>

<template>
  <div class="flex h-screen w-full overflow-hidden bg-surface">
    <!-- 左侧导航：毛玻璃侧栏 -->
    <aside class="la-glass w-[236px] shrink-0 flex flex-col border-r">
      <!-- 品牌 -->
      <div class="h-[56px] shrink-0 flex items-center gap-2.5 px-5">
        <div
          class="w-8 h-8 rounded-[9px] flex items-center justify-center text-white shrink-0"
          style="background: linear-gradient(160deg, #4ba3ff 0%, #007aff 100%); box-shadow: 0 1px 3px rgba(0, 122, 255, 0.32)"
        >
          <LaIcon name="sparkles" :size="17" :stroke-width="2" />
        </div>
        <div class="leading-tight min-w-0">
          <div class="text-[15px] font-semibold text-ink tracking-tight">LightAgent</div>
          <div class="text-[10.5px] text-muted mt-0.5">AI Agent Platform</div>
        </div>
      </div>

      <!-- 分组导航 -->
      <nav class="flex-1 overflow-y-auto px-2.5 pb-2">
        <div v-for="g in groups" :key="g.label" class="mt-3 first:mt-1">
          <div class="la-section-label px-2.5 mb-1.5">{{ g.label }}</div>
          <button
            v-for="m in g.items"
            :key="m.name"
            class="ios-press w-full flex items-center gap-2.5 px-2.5 h-[38px] rounded-[10px] text-[13.5px] mb-0.5"
            :class="
              activeMenu === m.name
                ? 'bg-[rgba(0,122,255,0.11)] text-primary font-semibold'
                : 'text-[rgba(60,60,67,0.78)] font-normal hover:bg-[rgba(120,120,128,0.08)]'
            "
            :aria-current="activeMenu === m.name ? 'page' : undefined"
            @click="go(m.name)"
          >
            <LaIcon :name="m.icon" :size="17" :stroke-width="activeMenu === m.name ? 2 : 1.8" />
            <span class="truncate">{{ m.label }}</span>
          </button>
        </div>
      </nav>

      <!-- 用户区（iOS 设置页底部账户卡） -->
      <div class="p-2.5 border-t border-line">
        <NDropdown :options="userOptions" trigger="click" placement="top-start" @select="onUserSelect">
          <button class="ios-press w-full flex items-center gap-2.5 px-2 py-2 rounded-[12px] hover:bg-[rgba(120,120,128,0.08)]">
            <span
              class="w-7 h-7 rounded-full text-white text-[12px] font-semibold flex items-center justify-center shrink-0"
              style="background: linear-gradient(160deg, #8e8e93 0%, #636366 100%)"
            >
              {{ (userStore.user?.username || 'U').slice(0, 1).toUpperCase() }}
            </span>
            <span class="min-w-0 flex-1 text-left leading-tight">
              <span class="block text-[13px] text-ink truncate">{{ userStore.user?.username || '未登录' }}</span>
              <span class="block text-[11px] text-muted truncate">
                {{ userStore.workspace?.name || '默认工作空间' }}
              </span>
            </span>
            <LaIcon name="more" :size="14" class="text-muted" />
          </button>
        </NDropdown>
      </div>
    </aside>

    <!-- 右侧主体 -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- 工具栏：毛玻璃吸顶 -->
      <header class="la-glass h-[52px] shrink-0 flex items-center justify-between px-6 border-b z-10">
        <div class="flex items-center gap-2 text-[13.5px] font-semibold text-ink tracking-tight">
          {{ title }}
        </div>
        <div class="flex items-center gap-2">
          <span
            class="inline-flex items-center gap-1.5 h-[26px] px-2.5 rounded-full text-[11.5px] text-[rgba(60,60,67,0.7)]"
            style="background: rgba(118, 118, 128, 0.08)"
          >
            <span class="w-1.5 h-1.5 rounded-full" style="background: #34c759"></span>
            {{ userStore.workspace?.name || '默认工作空间' }}
          </span>
        </div>
      </header>

      <main class="flex-1 overflow-y-auto">
        <div v-if="booting" class="h-full flex items-center justify-center">
          <NSpin size="small" />
        </div>
        <RouterView v-else />
      </main>
    </div>
  </div>
</template>
