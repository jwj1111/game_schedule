import { createApp } from 'vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/loading/style/css'
import './style.css'
import App from './App.vue'

import {
  Plus, Setting, ArrowLeft, ArrowRight,
} from '@element-plus/icons-vue'

// ===== 在 Element Plus 初始化前，覆盖根源变量 =====
const root = document.documentElement
const vars = {
  '--el-color-primary': '#111',
  '--el-color-primary-dark-2': '#000',
  '--el-color-primary-light-3': '#444',
  '--el-color-primary-light-5': '#666',
  '--el-color-primary-light-7': '#999',
  '--el-color-primary-light-8': '#ccc',
  '--el-color-primary-light-9': '#e5e5e5',
  '--el-input-border-color': '#e5e5e5',
  '--el-input-hover-border-color': '#ccc',
  '--el-input-focus-border-color': '#ccc',
  '--el-input-focus-border': '#ccc',
  '--el-select-border-color-hover': '#ccc',
  '--el-select-input-focus-border-color': '#ccc',
  '--el-border-color': '#e5e5e5',
  '--el-border-color-hover': '#ccc',
  '--el-border-color-focus': '#ccc',
  '--el-border-color-light': '#f0f0f0',
}
for (const [key, val] of Object.entries(vars)) {
  root.style.setProperty(key, val)
}

const app = createApp(App)

// 注册图标组件
const icons = { Plus, Setting, ArrowLeft, ArrowRight }
for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

// 导出 locale 供 App.vue 使用 ElConfigProvider
app.provide('elLocale', zhCn)

app.mount('#app')
