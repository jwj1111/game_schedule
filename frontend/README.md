# 前端模块 `frontend/`

Vite + Vue 3 + Element Plus + Tailwind CSS 构建的游戏排期日历看板。

---

## 文件清单

| 文件 / 目录 | 职责 |
| --- | --- |
| `vite.config.js` | Vite 配置：开发代理、Element Plus 按需导入、构建分包 |
| `package.json` | 依赖与脚本 |
| `src/main.js` | 应用入口：Element Plus 主题变量覆盖、图标注册、locale 注入 |
| `src/App.vue` | 根组件：数据加载、筛选逻辑、月份导航、子组件编排 |
| `src/style.css` | 全局样式：Tailwind 导入、动画关键帧、Element Plus 覆盖 |
| `src/api/index.js` | API 封装层：`fetch` 二次封装，所有后端接口调用 |
| `src/composables/useAuth.js` | 组合式函数：管理员登录状态与鉴权逻辑 |
| `src/utils/calendar.js` | 工具函数：月视图网格生成、按日期分组 |
| `src/utils/message.js` | 工具函数：统一消息提示封装 |
| `src/assets/` | 静态资源（banner 图等） |
| `src/components/` | 业务组件（见下方） |

### 组件清单

| 组件 | 职责 |
| --- | --- |
| `FilterBar.vue` | 多维度筛选栏（游戏/负责人/优先级/来源/资源位/日期范围/搜索） |
| `CalendarGrid.vue` | 月视图日历网格（6×7=42 格），标签化展示 |
| `DayDetail.vue` | 日期详情侧栏（Drawer），就地编辑优先级/资源位/别名/隐藏 |
| `StatsCard.vue` | 月度统计面板（优先级/来源/资源位/游戏/负责人分布） |
| `QuickManage.vue` | 按日期快速管理面板，横向日期 pill 切换 |
| `EventForm.vue` | 自定义事件新建/编辑弹窗 |
| `AnnotationForm.vue` | 爬虫数据标注编辑弹窗 |
| `SettingsPage.vue` | 设置页面（负责人管理 + 已隐藏事项恢复） |
| `DateWheelPicker.vue` | 移动端滚轮日期选择器（iOS 风格底部弹出） |
| `BottomSheetSelect.vue` | 移动端底部弹出多选面板 |
| `AdminLoginDialog.vue` | 管理员登录验证弹窗 |
| `NewsOverview.vue` | 资讯速览面板（近期重要事项概览） |
| `OverviewItemGroups.vue` | 速览事项按日分组展示子组件 |
| `TopSegmentSwitch.vue` | 顶部日历与速览视图分段切换器 |

---

## 常用命令

```powershell
# 开发（热更新，自动代理后端 /api → localhost:8000）
npm run dev

# 生产构建
npm run build

# 预览构建产物
npm run preview
```

---

## 依赖说明

| 依赖 | 用途 |
| --- | --- |
| `vue` | 核心框架（组合式 API setup） |
| `element-plus` | UI 组件库（按需自动导入） |
| `@element-plus/icons-vue` | 图标组件 |
| `tailwindcss` | 原子化 CSS（v4，CSS-first 配置） |
| `dayjs` | 日期处理 |
| `unplugin-auto-import` | Element Plus API 自动导入 |
| `unplugin-vue-components` | Element Plus 组件自动注册 |

---

## API 调用清单

所有接口封装在 `src/api/index.js`，开发环境通过 Vite proxy 代理到后端。

| 函数 | 方法 | 路径 | 说明 |
| --- | --- | --- | --- |
| `loginAdmin()` | POST | `/api/auth/login` | 管理员密码登录 |
| `fetchAuthStatus()` | GET | `/api/auth/status` | 查询管理员登录状态 |
| `logoutAdmin()` | POST | `/api/auth/logout` | 退出管理员登录 |
| `fetchCalendar()` | GET | `/api/calendar` | 统一日历查询（支持日期/游戏/负责人/关键词筛选） |
| `fetchOverview()` | GET | `/api/overview` | 资讯速览查询（当天+未来15天+过去7天） |
| `fetchGames()` | GET | `/api/games` | 游戏名列表 |
| `fetchOwnerNames()` | GET | `/api/owner-names` | 负责人姓名列表 |
| `fetchHidden()` | GET | `/api/hidden` | 已隐藏的爬虫数据 |
| `updateAnnotation()` | PUT | `/api/annotations/{id}` | 更新爬虫数据标注 |
| `createEvent()` | POST | `/api/events` | 新建自定义事件 |
| `updateEvent()` | PUT | `/api/events/{id}` | 修改事件 |
| `deleteEvent()` | DELETE | `/api/events/{id}` | 删除事件 |
| `fetchOwners()` | GET | `/api/owners` | 全部游戏负责人 |
| `createOwner()` | POST | `/api/owners` | 新增游戏负责人 |
| `updateOwner()` | PUT | `/api/owners/{game}` | 修改负责人列表 |

---

## 数据流

```
App.vue onMounted
  ├── fetchCalendar(start, end, filters)  → calendarData → dataByDate
  ├── fetchGames()                        → gameOptions
  └── fetchOwnerNames()                   → ownerOptions

用户操作（编辑/删除/隐藏）
  → 调用对应 API
  → 就地更新 calendarData（不重新请求整月接口）
  → 响应式驱动视图刷新
```

---

## 构建产物

生产构建自动分包：

| chunk | 内容 |
| --- | --- |
| `index-*.js` | 应用代码 + Vue 运行时 |
| `vendor-element-*.js` | Element Plus（独立缓存） |
| `vendor-dayjs-*.js` | dayjs（独立缓存） |
| `DayDetail-*.js` 等 | 懒加载组件（弹窗/侧栏，按需加载） |

构建产物输出到 `dist/`（Git 忽略），线上由 Docker + Nginx 托管。

---

## 设计约定

- **响应式双布局**：PC 端与移动端共用组件，通过 Tailwind 断点（`md:`）切换布局
- **主题色**：黑白灰设计语言，通过 `main.js` 覆盖 Element Plus CSS 变量
- **就地更新**：CRUD 操作后直接修改前端响应式状态，避免重新请求
- **移动端交互**：底部弹出面板（`BottomSheetSelect`、`DateWheelPicker`）替代 PC 下拉框
