<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const TOKEN_KEY = 'game_schedule_admin_token'

function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}

// 页面准入状态
const authorized = ref(false)

async function request(path, options = {}) {
  const token = getToken()
  if (!token) {
    redirectToMain('未登录')
    return null
  }
  const headers = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
    ...(options.headers || {}),
  }
  try {
    const res = await fetch(`/api/dbadmin${path}`, { ...options, headers })
    if (res.status === 401) {
      redirectToMain('登录已失效')
      return null
    }
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${res.status}`)
    }
    return res.json()
  } catch (e) {
    if (e.message?.includes('fetch')) throw new Error('网络连接失败，请检查后端是否启动')
    throw new Error(e.message || '请求失败')
  }
}

function redirectToMain(reason) {
  ElMessage.warning(`${reason}，正在跳转回主页...`)
  setTimeout(() => { window.location.href = '/' }, 1200)
}

// ==================== 状态 ====================
const tables = ref([])
const activeTable = ref('')
const tableSchema = ref([])
const tableRows = ref([])
const loading = ref(false)
const schemaLoading = ref(false)

// 分页
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const totalPages = ref(1)

// 排序
const sortBy = ref(null)
const sortOrder = ref('asc')

// 新增/编辑弹窗
const formVisible = ref(false)
const formMode = ref('create') // 'create' | 'edit'
const formData = ref({})
const formSaving = ref(false)

// ==================== 加载 ====================
let rowsRequestId = 0 // 竞态保护：只接受最新请求的结果

async function loadTables() {
  // 准入校验：无 token 直接拦截
  if (!getToken()) {
    redirectToMain('未登录')
    return
  }
  loading.value = true
  try {
    const res = await request('/tables')
    if (res) {
      tables.value = res.tables || []
      authorized.value = true
    }
  } catch (e) {
    ElMessage.error('加载表列表失败: ' + e.message)
  } finally {
    loading.value = false
  }
}

async function loadSchema(tableName) {
  schemaLoading.value = true
  try {
    const res = await request(`/tables/${encodeURIComponent(tableName)}/schema`)
    if (res) tableSchema.value = res.columns || []
  } catch (e) {
    ElMessage.error('加载表结构失败: ' + e.message)
    tableSchema.value = []
  } finally {
    schemaLoading.value = false
  }
}

async function loadRows() {
  if (!activeTable.value) return
  const reqId = ++rowsRequestId
  loading.value = true
  try {
    const params = new URLSearchParams({ page: page.value, page_size: pageSize.value })
    if (sortBy.value) {
      params.set('sort_by', sortBy.value)
      params.set('sort_order', sortOrder.value)
    }
    const res = await request(`/tables/${encodeURIComponent(activeTable.value)}/rows?${params}`)
    // 竞态保护：如果切换了表，丢弃旧结果
    if (reqId !== rowsRequestId) return
    if (res) {
      tableRows.value = res.rows || []
      total.value = res.total || 0
      totalPages.value = res.total_pages || 1
    }
  } catch (e) {
    if (reqId !== rowsRequestId) return
    ElMessage.error('加载数据失败: ' + e.message)
  } finally {
    if (reqId === rowsRequestId) loading.value = false
  }
}

async function selectTable(tableName) {
  activeTable.value = tableName
  page.value = 1
  sortBy.value = null
  sortOrder.value = 'asc'
  await Promise.all([loadSchema(tableName), loadRows()])
}

function onSortChange({ prop, order }) {
  sortBy.value = prop || null
  sortOrder.value = order === 'descending' ? 'desc' : 'asc'
  page.value = 1
  loadRows()
}

function onPageChange(p) {
  page.value = p
  loadRows()
}

function onSizeChange(s) {
  pageSize.value = s
  page.value = 1
  loadRows()
}

// ==================== 新增 ====================
const AUTO_FIELDS = ['created_at', 'updated_at']
function isAutoField(name) { return AUTO_FIELDS.includes(name.toLowerCase()) }

function openCreateForm() {
  formMode.value = 'create'
  const data = {}
  for (const col of tableSchema.value) {
    if (col.primary_key) continue
    if (isAutoField(col.name)) continue
    data[col.name] = col.nullable ? null : ''
  }
  formData.value = data
  formVisible.value = true
}

// ==================== 编辑 ====================
function openEditForm(row) {
  formMode.value = 'edit'
  formData.value = { ...row }
  formVisible.value = true
}

// ==================== 保存 ====================
async function onSaveForm() {
  // 必填校验
  const cols = formMode.value === 'create' ? editableColumns.value : editableColumns.value
  for (const col of cols) {
    if (!col.nullable && !col.primary_key && !isAutoField(col.name)) {
      const val = formData.value[col.name]
      if (val === null || val === undefined || val === '') {
        ElMessage.warning(`"${col.name}" 为必填字段`)
        return
      }
    }
  }

  formSaving.value = true
  try {
    if (formMode.value === 'create') {
      const res = await request(`/tables/${encodeURIComponent(activeTable.value)}/rows`, {
        method: 'POST',
        body: JSON.stringify(formData.value),
      })
      if (res) {
        ElMessage.success('新增成功')
        formVisible.value = false
        await loadRows()
      }
    } else {
      const pk = tableSchema.value.find(c => c.primary_key)
      if (!pk) { ElMessage.error('无法确定主键'); return }
      const id = formData.value[pk.name]
      const payload = { ...formData.value }
      delete payload[pk.name]
      // 排除自动生成字段
      for (const key of Object.keys(payload)) {
        if (isAutoField(key)) delete payload[key]
      }
      const res = await request(`/tables/${encodeURIComponent(activeTable.value)}/rows/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload),
      })
      if (res) {
        ElMessage.success('更新成功')
        formVisible.value = false
        await loadRows()
      }
    }
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    formSaving.value = false
  }
}

// ==================== 删除 ====================
async function onDeleteRow(row) {
  const pk = tableSchema.value.find(c => c.primary_key)
  if (!pk) { ElMessage.error('无法确定主键'); return }
  const id = row[pk.name]
  try {
    await ElMessageBox.confirm(
      `确定删除 ${pk.name}=${id} 这条记录？此操作不可撤销。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    const res = await request(`/tables/${encodeURIComponent(activeTable.value)}/rows/${id}`, {
      method: 'DELETE',
    })
    if (res) {
      ElMessage.success('删除成功')
      await loadRows()
    }
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

// ==================== 刷新 ====================
function refresh() {
  if (activeTable.value) loadRows()
}

// ==================== 返回主页 ====================
function goBack() {
  window.close()
  // 如果 window.close 无效（非脚本打开的窗口），跳转到主页
  setTimeout(() => { window.location.href = '/' }, 300)
}

// ==================== 辅助 ====================
const primaryKeyName = computed(() => {
  const pk = tableSchema.value.find(c => c.primary_key)
  return pk?.name || 'id'
})

const editableColumns = computed(() =>
  tableSchema.value.filter(c => !c.primary_key && !isAutoField(c.name))
)

function formatCellValue(val) {
  if (val === null || val === undefined) return '—'
  if (typeof val === 'boolean') return val ? '✓' : '✗'
  if (typeof val === 'object') return JSON.stringify(val)
  return String(val)
}

function getColumnWidth(col) {
  const name = col.name.toLowerCase()
  if (name === 'id') return 70
  if (name.includes('link') || name.includes('url')) return 200
  if (name.includes('info') || name.includes('description')) return 250
  if (name.includes('date') || name.includes('_at')) return 150
  if (name.includes('game')) return 120
  if (col.type?.includes('BOOL')) return 80
  return undefined
}

onMounted(loadTables)
</script>

<template>
  <div class="dbadmin-root">
    <!-- 未授权时显示加载/跳转提示 -->
    <div v-if="!authorized" class="auth-gate">
      <div class="auth-gate-inner">
        <div class="auth-spinner"></div>
        <p>验证管理员权限中...</p>
      </div>
    </div>

    <template v-else>
    <!-- 顶栏 -->
    <header class="dbadmin-header">
      <div class="header-left">
        <button class="back-btn" @click="goBack" title="返回主页">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </button>
        <h1 class="header-title">数据管理</h1>
        <span class="header-badge">管理员</span>
      </div>
      <div class="header-right">
        <span class="header-hint">此页面仅管理员可见</span>
      </div>
    </header>

    <div class="dbadmin-body">
      <!-- 左侧表列表 -->
      <aside class="table-sidebar">
        <div class="sidebar-title">数据表</div>
        <div
          v-for="t in tables"
          :key="t"
          class="table-item"
          :class="{ active: activeTable === t }"
          @click="selectTable(t)"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M3 15h18M9 3v18"/>
          </svg>
          <span>{{ t }}</span>
        </div>
        <div v-if="!tables.length && !loading" class="sidebar-empty">暂无数据表</div>
      </aside>

      <!-- 右侧内容区 -->
      <main class="table-content">
        <!-- 未选表 -->
        <div v-if="!activeTable" class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5">
            <rect x="3" y="3" width="18" height="18" rx="2"/>
            <path d="M3 9h18M3 15h18M9 3v18"/>
          </svg>
          <p>请从左侧选择一个数据表</p>
        </div>

        <template v-else>
          <!-- 表结构概览 -->
          <div class="schema-bar">
            <div class="schema-bar-left">
              <span class="schema-table-name">{{ activeTable }}</span>
              <span class="schema-count">{{ total }} 条记录</span>
            </div>
            <div class="schema-bar-right">
              <el-popover trigger="hover" placement="bottom-start" :width="420">
                <template #reference>
                  <button class="action-btn">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
                    </svg>
                    表结构
                  </button>
                </template>
                <div class="schema-popover">
                  <table class="schema-table">
                    <thead>
                      <tr><th>列名</th><th>类型</th><th>可空</th><th>主键</th><th>默认值</th></tr>
                    </thead>
                    <tbody>
                      <tr v-for="col in tableSchema" :key="col.name">
                        <td class="col-name">{{ col.name }}</td>
                        <td class="col-type">{{ col.type }}</td>
                        <td>{{ col.nullable ? '是' : '否' }}</td>
                        <td>{{ col.primary_key ? '✓' : '' }}</td>
                        <td class="col-default">{{ col.default || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </el-popover>
              <button class="action-btn" @click="openCreateForm">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 5v14M5 12h14"/>
                </svg>
                新增
              </button>
              <button class="action-btn" @click="refresh">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 4v6h6M23 20v-6h-6"/>
                  <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
                </svg>
                刷新
              </button>
            </div>
          </div>

          <!-- 数据表格 -->
          <div v-loading="loading" class="data-table-wrap">
            <el-table
              :data="tableRows"
              stripe
              border
              size="small"
              max-height="calc(100vh - 230px)"
              style="width: 100%"
              @sort-change="onSortChange"
              :default-sort="sortBy ? { prop: sortBy, order: sortOrder === 'desc' ? 'descending' : 'ascending' } : {}"
            >
              <el-table-column
                v-for="col in tableSchema"
                :key="col.name"
                :prop="col.name"
                :label="col.name"
                :sortable="'custom'"
                :min-width="getColumnWidth(col) || 100"
                show-overflow-tooltip
              >
                <template #default="{ row }">
                  <span :class="{ 'cell-null': row[col.name] === null || row[col.name] === undefined }">
                    {{ formatCellValue(row[col.name]) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <button class="row-action-btn edit" @click="openEditForm(row)" title="编辑">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                  <button class="row-action-btn delete" @click="onDeleteRow(row)" title="删除">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                  </button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 分页 -->
          <div class="pagination-bar">
            <el-pagination
              v-model:current-page="page"
              v-model:page-size="pageSize"
              :total="total"
              :page-sizes="[20, 50, 100, 200]"
              layout="total, sizes, prev, pager, next"
              small
              background
              @current-change="onPageChange"
              @size-change="onSizeChange"
            />
          </div>
        </template>
      </main>
    </div>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="formVisible"
      :title="formMode === 'create' ? `新增记录 - ${activeTable}` : `编辑记录 - ${activeTable}`"
      width="560px"
      :close-on-click-modal="false"
      append-to-body
      destroy-on-close
    >
      <el-form label-width="120px" label-position="left" size="default">
        <el-form-item
          v-for="col in (formMode === 'create' ? editableColumns : tableSchema)"
          :key="col.name"
          :label="col.name"
        >
          <template v-if="(col.primary_key || isAutoField(col.name)) && formMode === 'edit'">
            <el-input :model-value="String(formData[col.name] ?? '')" disabled />
          </template>
          <template v-else-if="col.type?.includes('BOOL')">
            <el-switch v-model="formData[col.name]" />
          </template>
          <template v-else-if="col.type?.includes('INT')">
            <el-input-number v-model="formData[col.name]" :controls="false" style="width: 100%" />
          </template>
          <template v-else-if="col.type?.includes('JSON')">
            <el-input v-model="formData[col.name]" type="textarea" :rows="3" placeholder="JSON 格式" />
          </template>
          <template v-else-if="col.type?.includes('TEXT') || col.name.includes('info') || col.name.includes('description')">
            <el-input v-model="formData[col.name]" type="textarea" :rows="2" />
          </template>
          <template v-else>
            <el-input v-model="formData[col.name]" />
          </template>
          <div class="field-meta">
            {{ col.type }}{{ col.nullable ? ' · 可空' : ' · 必填' }}
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="formSaving" @click="onSaveForm">
          {{ formMode === 'create' ? '新增' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
    </template>
  </div>
</template>

<style>
/* ===== 全局重置 ===== */
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100%; }
body {
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: #f5f5f5;
  color: #333;
  font-size: 13px;
  -webkit-font-smoothing: antialiased;
}

/* ===== 准入验证 ===== */
.auth-gate {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
}
.auth-gate-inner {
  text-align: center;
  color: #999;
  font-size: 14px;
}
.auth-spinner {
  width: 24px;
  height: 24px;
  margin: 0 auto 12px;
  border: 2px solid #e5e5e5;
  border-top-color: #111;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ===== 布局 ===== */
.dbadmin-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.dbadmin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
  padding: 0 20px;
  background: #111;
  color: #fff;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}
.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 6px;
  background: transparent;
  color: #fff;
  cursor: pointer;
  transition: background 150ms, border-color 150ms;
}
.back-btn:hover {
  background: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.4);
}
.header-title {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.header-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 10px;
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.7);
}
.header-right {
  display: flex;
  align-items: center;
}
.header-hint {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
}

.dbadmin-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ===== 左侧表列表 ===== */
.table-sidebar {
  width: 200px;
  flex-shrink: 0;
  background: #fff;
  border-right: 1px solid #e8e8e8;
  overflow-y: auto;
  padding: 12px 0;
}
.sidebar-title {
  padding: 0 16px 8px;
  font-size: 11px;
  color: #999;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.table-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  cursor: pointer;
  color: #555;
  font-size: 13px;
  transition: background 120ms, color 120ms;
}
.table-item:hover {
  background: #f5f5f5;
  color: #111;
}
.table-item.active {
  background: #f0f0f0;
  color: #111;
  font-weight: 600;
}
.sidebar-empty {
  padding: 20px 16px;
  color: #ccc;
  font-size: 12px;
  text-align: center;
}

/* ===== 右侧内容 ===== */
.table-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 16px 20px;
  gap: 12px;
}

.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #ccc;
  font-size: 14px;
}

/* ===== 操作栏 ===== */
.schema-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
}
.schema-bar-left {
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.schema-table-name {
  font-size: 16px;
  font-weight: 700;
  color: #111;
}
.schema-count {
  font-size: 12px;
  color: #999;
  font-variant-numeric: tabular-nums;
}
.schema-bar-right {
  display: flex;
  gap: 6px;
}
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  background: #fff;
  color: #555;
  font-size: 12px;
  cursor: pointer;
  transition: all 120ms;
}
.action-btn:hover {
  background: #f5f5f5;
  color: #111;
  border-color: #ccc;
}

/* ===== 表结构弹出 ===== */
.schema-popover { max-height: 320px; overflow-y: auto; }
.schema-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.schema-table th {
  text-align: left;
  padding: 6px 8px;
  background: #f9f9f9;
  color: #999;
  font-weight: 600;
  border-bottom: 1px solid #eee;
}
.schema-table td {
  padding: 5px 8px;
  border-bottom: 1px solid #f0f0f0;
  color: #555;
}
.col-name { font-weight: 600; color: #111; }
.col-type { font-family: monospace; font-size: 11px; color: #888; }
.col-default { font-family: monospace; font-size: 11px; color: #aaa; }

/* ===== 数据表格 ===== */
.data-table-wrap {
  flex: 1;
  overflow: hidden;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  background: #fff;
}
.cell-null { color: #ccc; font-style: italic; }

/* ===== 行操作按钮 ===== */
.row-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 1px solid #e5e5e5;
  border-radius: 5px;
  background: #fff;
  cursor: pointer;
  color: #999;
  margin-right: 4px;
  transition: all 120ms;
}
.row-action-btn.edit:hover { color: #111; border-color: #111; }
.row-action-btn.delete:hover { color: #e74c3c; border-color: #e74c3c; }

/* ===== 分页 ===== */
.pagination-bar {
  display: flex;
  justify-content: flex-end;
  flex-shrink: 0;
  padding-top: 4px;
}

/* ===== 表单字段元信息 ===== */
.field-meta {
  font-size: 11px;
  color: #bbb;
  margin-top: 2px;
  font-family: monospace;
}

/* ===== Element Plus 黑白主题覆盖 ===== */
.el-button--primary {
  --el-button-bg-color: #111 !important;
  --el-button-border-color: #111 !important;
  --el-button-hover-bg-color: #333 !important;
  --el-button-hover-border-color: #333 !important;
}
.el-table th.el-table__cell {
  background: #fafafa !important;
  color: #666 !important;
  font-weight: 600 !important;
  font-size: 12px !important;
}
.el-pagination.is-background .el-pager li.is-active {
  background: #111 !important;
}
.el-dialog__title {
  font-weight: 600 !important;
  font-size: 15px !important;
  color: #111 !important;
}
</style>
