import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import 'element-plus/dist/index.css'
import './style.css'
import App from './App.vue'

import {
  Plus, Setting, ArrowLeft, ArrowRight,
  CircleCheckFilled, Hide, CircleCheck,
} from '@element-plus/icons-vue'

// ===== 在 Element Plus 初始化前，覆盖根源变量 =====
// Element Plus 内部用 --el-color-primary 计算所有派生色
// 在 DOM 根元素上设置后，所有组件计算出的 focus/hover 色都会跟着变
const root = document.documentElement
const vars = {
  '--el-color-primary': '#111',
  '--el-color-primary-dark-2': '#000',
  '--el-color-primary-light-3': '#444',
  '--el-color-primary-light-5': '#666',
  '--el-color-primary-light-7': '#999',
  '--el-color-primary-light-8': '#ccc',
  '--el-color-primary-light-9': '#e5e5e5',
  // 输入框边框色（Element Plus 内部读这些变量）
  '--el-input-border-color': '#e5e5e5',
  '--el-input-hover-border-color': '#ccc',
  '--el-input-focus-border-color': '#ccc',
  '--el-input-focus-border': '#ccc',
  // Select
  '--el-select-border-color-hover': '#ccc',
  '--el-select-input-focus-border-color': '#ccc',
  // 通用边框
  '--el-border-color': '#e5e5e5',
  '--el-border-color-hover': '#ccc',
  '--el-border-color-focus': '#ccc',
  '--el-border-color-light': '#f0f0f0',
}
for (const [key, val] of Object.entries(vars)) {
  root.style.setProperty(key, val)
}

const app = createApp(App)
app.use(ElementPlus, { locale: zhCn })

const icons = { Plus, Setting, ArrowLeft, ArrowRight, CircleCheckFilled, Hide, CircleCheck }
for (const [key, component] of Object.entries(icons)) {
  app.component(key, component)
}

app.mount('#app')
