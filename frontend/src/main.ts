import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createDiscreteApi } from 'naive-ui'
import App from './App.vue'
import router from './router'
import { setNotifier } from './api/client'
import './styles/index.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// 全局消息提示（脱离组件树，供 axios 拦截器使用）
const { message } = createDiscreteApi(['message'], {
  configProviderProps: { themeOverrides: { common: { primaryColor: '#2563EB' } } },
})
setNotifier((msg: string) => message.error(msg))

app.mount('#app')
