<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { RouterView, RouterLink, useRoute, useRouter } from 'vue-router'
import { NDropdown, NSpin, useMessage } from 'naive-ui'
import LaIcon from '@/components/common/LaIcon.vue'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const message = useMessage()
const userStore = useUserStore()
const booting = ref(true)

/** 侧栏分组：与参考项目一致，一级菜单带专属语义图标 */
const groups = [
  { label: '工作台', items: [
    { name: 'dashboard', label: '工作空间', icon: 'dashboard' },
    { name: 'applications', label: '应用管理', icon: 'apps' },
    { name: 'workflows', label: '工作流', icon: 'flow' },
  ] },
  { label: '资源', items: [
    { name: 'knowledge', label: '知识库', icon: 'book' },
    { name: 'tools', label: '工具管理', icon: 'tool' },
    { name: 'models', label: '模型管理', icon: 'cpu' },
  ] },
  { label: '系统', items: [
    { name: 'logs', label: '运行日志', icon: 'logs' },
    { name: 'settings', label: '系统设置', icon: 'settings' },
  ] },
]

const groupOf = (name: string) => groups.find(g => g.items.some(i => i.name === name))?.label || ''

const activeMenu = computed(() => {
  const path = route.path
  if (path.startsWith('/applications/')) return 'applications'
  if (path.startsWith('/knowledge/')) return 'knowledge'
  if (path.startsWith('/workflows/')) return 'workflows'
  return (route.name as string) || 'dashboard'
})

const title = computed(() => (route.meta.title as string) || 'LightAgent')
const pageGroup = computed(() => groupOf(activeMenu.value))
const displayName = computed(() => userStore.user?.username || '管理员')
const userInitial = computed(() => (displayName.value || 'U').slice(0, 1).toUpperCase())
const workspaceName = computed(() => userStore.workspace?.name || '默认工作空间')

/** 侧栏折叠状态持久化（参考项目 localStorage 方案） */
const collapsed = ref(localStorage.getItem('la-sidebar-collapsed') === 'yes')
const mobileOpen = ref(false)
function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem('la-sidebar-collapsed', collapsed.value ? 'yes' : 'no')
}

/** 用户菜单：带图标与分隔线（skill: 菜单项需清晰语义与图标，危险操作单独区分） */
const userOptions = computed(() => [
  {
    key: 'account-header',
    type: 'render',
    render: () => h('div', { class: 'la-user-menu__head' }, [
      h('span', { class: 'la-user-menu__head-name' }, displayName.value),
      h('span', { class: 'la-user-menu__head-sub' }, workspaceName.value),
    ]),
  },
  { key: 'divider-1', type: 'divider' },
  { label: '账号设置', key: 'settings', icon: () => h(LaIcon, { name: 'settings', size: 15 }) },
  {
    label: '退出登录',
    key: 'logout',
    icon: () => h(LaIcon, { name: 'logout', size: 15 }),
    props: { class: 'la-user-menu__danger' },
  },
])

/** 菜单打开状态（用于 aria-expanded 与 chevron 旋转） */
const userMenuOpen = ref(false)

function go(name: string) {
  router.push({ name })
  mobileOpen.value = false
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
  <div class="la-admin-layout" :class="{ 'la-admin-layout--collapsed': collapsed }">
    <a class="la-admin-skip" href="#la-main-content">跳到主要内容</a>

    <!-- 侧栏 -->
    <aside class="la-admin-sidebar" :class="{ 'la-admin-sidebar--mobile-open': mobileOpen }">
      <button class="la-admin-brand" type="button" aria-label="返回工作空间" @click="go('dashboard')">
        <span class="la-admin-brand-mark" aria-hidden="true">
          <LaIcon name="sparkles" :size="22" />
        </span>
        <span class="la-admin-brand-copy">
          <strong>LightAgent</strong>
          <small>AI AGENT PLATFORM</small>
        </span>
      </button>

      <nav class="la-admin-nav" aria-label="主菜单">
        <div v-for="g in groups" :key="g.label" class="la-admin-nav-group">
          <div class="la-admin-group-label">{{ g.label }}</div>
          <button
            v-for="m in g.items"
            :key="m.name"
            type="button"
            class="la-admin-menu-item"
            :class="{ 'la-admin-menu-item--active': activeMenu === m.name }"
            :aria-current="activeMenu === m.name ? 'page' : undefined"
            :title="collapsed ? m.label : undefined"
            @click="go(m.name)"
          >
            <span class="la-admin-menu-icon" aria-hidden="true">
              <LaIcon :name="m.icon" :size="18" />
            </span>
            <span class="la-admin-menu-label">{{ m.label }}</span>
          </button>
        </div>
      </nav>

      <div class="la-admin-sidebar-footer">
        <button
          class="la-admin-collapse"
          type="button"
          :aria-label="collapsed ? '展开侧边栏' : '收起侧边栏'"
          :title="collapsed ? '展开侧边栏' : '收起侧边栏'"
          @click="toggleSidebar"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m13.5 7-5 5 5 5" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
            <path d="m18.5 7-5 5 5 5" stroke="currentColor" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" opacity="0.38" />
          </svg>
        </button>
      </div>
    </aside>

    <button v-if="mobileOpen" class="la-admin-mask" type="button" aria-label="关闭菜单" @click="mobileOpen = false" />

    <!-- 主体 -->
    <div class="la-admin-body">
      <header class="la-admin-header">
        <div style="display:flex;align-items:center;min-width:0">
          <button class="la-admin-header-menu" type="button" aria-label="打开菜单" @click="mobileOpen = true">
            <LaIcon name="more" :size="18" />
          </button>
          <nav class="la-admin-breadcrumb" aria-label="面包屑">
            <RouterLink v-if="route.path !== '/dashboard'" to="/dashboard">平台管理中心</RouterLink>
            <span v-else class="la-admin-breadcrumb-root">平台管理中心</span>
            <template v-if="pageGroup">
              <span class="la-admin-breadcrumb-sep la-admin-breadcrumb-sep--group" aria-hidden="true">
                <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="m4.2 2.25 3.5 3.75-3.5 3.75" /></svg>
              </span>
              <span class="la-admin-breadcrumb-group">{{ pageGroup }}</span>
            </template>
            <span class="la-admin-breadcrumb-sep" aria-hidden="true">
              <svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"><path d="m4.2 2.25 3.5 3.75-3.5 3.75" /></svg>
            </span>
            <strong class="la-admin-breadcrumb-current" aria-current="page">{{ title }}</strong>
          </nav>
        </div>

        <div class="la-admin-header__actions">
          <NDropdown
            :options="userOptions"
            trigger="click"
            placement="bottom-end"
            :show-arrow="false"
            class="la-user-menu"
            @select="onUserSelect"
            @update:show="(v: boolean) => (userMenuOpen = v)"
          >
            <button
              class="la-admin-user-trigger"
              type="button"
              :aria-label="`当前登录用户：${displayName}，${workspaceName}，打开账户菜单`"
              aria-haspopup="menu"
              :aria-expanded="userMenuOpen"
            >
              <span class="la-admin-avatar" aria-hidden="true">{{ userInitial }}</span>
              <span class="la-admin-user-summary">
                <strong :title="displayName">{{ displayName }}</strong>
                <small :title="workspaceName">{{ workspaceName }}</small>
              </span>
              <span class="la-admin-user-chevron" :class="{ 'is-open': userMenuOpen }" aria-hidden="true" />
            </button>
          </NDropdown>
        </div>
      </header>

      <main id="la-main-content" class="la-admin-main" tabindex="-1">
        <div v-if="booting" style="height:100%;display:flex;align-items:center;justify-content:center">
          <NSpin />
        </div>
        <RouterView v-else v-slot="{ Component, route: currentRoute }">
          <Transition name="la-admin-page" mode="out-in">
            <component :is="Component" :key="currentRoute.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
