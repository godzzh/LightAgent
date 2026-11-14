import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import { setToken, getToken } from '@/api/client'
import type { User, Workspace } from '@/types'

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const workspace = ref<Workspace | null>(null)
  const loaded = ref(false)
  const loading = ref(false)

  async function login(account: string, password: string) {
    loading.value = true
    try {
      const res = await authApi.login(account, password)
      setToken(res.access_token)
      user.value = res.user
      workspace.value = res.workspace
      loaded.value = true
      return res
    } finally {
      loading.value = false
    }
  }

  async function fetchMe(force = false) {
    if (!getToken()) return null
    if (loaded.value && !force) return user.value
    loading.value = true
    try {
      const res = await authApi.me()
      user.value = res.user
      workspace.value = res.workspace
      loaded.value = true
      return res.user
    } catch {
      user.value = null
      workspace.value = null
      return null
    } finally {
      loading.value = false
    }
  }

  function logout() {
    setToken('')
    user.value = null
    workspace.value = null
    loaded.value = false
  }

  return { user, workspace, loaded, loading, login, fetchMe, logout }
})
