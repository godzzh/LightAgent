import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { getToken } from '@/api/client'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '工作空间', icon: 'dashboard' },
      },
      {
        path: 'applications',
        name: 'applications',
        component: () => import('@/views/applications/ApplicationsView.vue'),
        meta: { title: '应用管理', icon: 'apps' },
      },
      {
        path: 'applications/:id/agent',
        name: 'agent-editor',
        component: () => import('@/views/agent/AgentEditorView.vue'),
        meta: { title: 'Agent 调试', hideInMenu: true },
      },
      {
        path: 'applications/:id/publish',
        name: 'app-publish',
        component: () => import('@/views/applications/PublishView.vue'),
        meta: { title: '应用发布', hideInMenu: true },
      },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/knowledge/KnowledgeView.vue'),
        meta: { title: '知识库', icon: 'book' },
      },
      {
        path: 'knowledge/:id',
        name: 'knowledge-detail',
        component: () => import('@/views/knowledge/DatasetDetailView.vue'),
        meta: { title: '知识库详情', hideInMenu: true },
      },
      {
        path: 'tools',
        name: 'tools',
        component: () => import('@/views/tools/ToolsView.vue'),
        meta: { title: '工具管理', icon: 'tool' },
      },
      {
        path: 'models',
        name: 'models',
        component: () => import('@/views/models/ModelsView.vue'),
        meta: { title: '模型管理', icon: 'cpu' },
      },
      {
        path: 'workflows',
        name: 'workflows',
        component: () => import('@/views/workflow/WorkflowListView.vue'),
        meta: { title: '工作流', icon: 'flow' },
      },
      {
        path: 'workflows/:id',
        name: 'workflow-editor',
        component: () => import('@/views/workflow/WorkflowEditorView.vue'),
        meta: { title: '工作流编辑器', hideInMenu: true, fullscreen: true },
      },
      {
        path: 'logs',
        name: 'logs',
        component: () => import('@/views/logs/LogsView.vue'),
        meta: { title: '运行日志', icon: 'logs' },
      },
      {
        path: 'settings',
        name: 'settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { title: '系统设置', icon: 'settings' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · LightAgent` : 'LightAgent'
  if (to.meta.public) return true
  if (!getToken()) return { name: 'login', query: { redirect: to.fullPath } }
  return true
})

export default router
