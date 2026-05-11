<script setup>
import { ref, computed, onMounted, watch, nextTick, inject, defineAsyncComponent } from 'vue'
import { ElConfigProvider } from 'element-plus'
import dayjs from 'dayjs'
import { message } from './utils/message.js'

const ElMessage = message
const elLocale = inject('elLocale')
import CalendarGrid from './components/CalendarGrid.vue'
import FilterBar from './components/FilterBar.vue'
import StatsCard from './components/StatsCard.vue'
import QuickManage from './components/QuickManage.vue'
import TopSegmentSwitch from './components/TopSegmentSwitch.vue'
import SettingsPage from './components/SettingsPage.vue'
import NewsOverview from './components/NewsOverview.vue'
import AdminLoginDialog from './components/AdminLoginDialog.vue'
import { useAuth } from './composables/useAuth.js'

// 懒加载：非首屏关键组件（弹窗/侧栏，用户交互后才需要）
const DayDetail = defineAsyncComponent(() => import('./components/DayDetail.vue'))
const AnnotationForm = defineAsyncComponent(() => import('./components/AnnotationForm.vue'))
const EventForm = defineAsyncComponent(() => import('./components/EventForm.vue'))
import {
  fetchCalendar, fetchOverview, fetchGames, fetchOwnerNames,
  updateAnnotation,
  createEvent, updateEvent, deleteEvent as apiDeleteEvent,
  createOwner,
} from './api/index.js'
import { generateMonthGrid, groupByDate } from './utils/calendar.js'

const {
  isAdmin,
  authLoading,
  loginDialogVisible,
  refreshAuthStatus,
  login,
  logout,
  openLoginDialog,
  requireAdminAction,
} = useAuth()

// ==================== 月份导航 ====================
const currentYear = ref(dayjs().year())
const currentMonth = ref(dayjs().month() + 1)
const monthLabel = computed(() => `${currentYear.value} 年 ${currentMonth.value} 月`)

// 范围限制：过去 6 个月 ~ 未来 12 个月
const minMonth = dayjs().subtract(6, 'month').startOf('month')
const maxMonth = dayjs().add(12, 'month').startOf('month')

const currentDayjs = computed(() =>
  dayjs(`${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}-01`)
)
const canPrev = computed(() => currentDayjs.value.isAfter(minMonth))
const canNext = computed(() => currentDayjs.value.isBefore(maxMonth))

const slideDirection = ref('right') // 月份切换方向

function prevMonth() {
  if (!canPrev.value) return
  slideDirection.value = 'left'
  const d = currentDayjs.value.subtract(1, 'month')
  currentYear.value = d.year()
  currentMonth.value = d.month() + 1
}
function nextMonth() {
  if (!canNext.value) return
  slideDirection.value = 'right'
  const d = currentDayjs.value.add(1, 'month')
  currentYear.value = d.year()
  currentMonth.value = d.month() + 1
}
function goToday() {
  const todayMonth = dayjs().month() + 1
  const todayYear = dayjs().year()
  slideDirection.value = dayjs(`${todayYear}-${todayMonth}-01`).isAfter(currentDayjs.value) ? 'right' : 'left'
  currentYear.value = todayYear
  currentMonth.value = todayMonth
}

// ==================== 日期范围筛选 ====================
const dateRange = ref(null)

// ==================== 日历网格 ====================
const days = computed(() => generateMonthGrid(currentYear.value, currentMonth.value))

// ==================== 数据 ====================
const calendarData = ref([])
const gameOptions = ref([])
const ownerOptions = ref([])
const loading = ref(false)
const filterGames = ref('')
const filterOwners = ref('')
const filterKeyword = ref('')

// ==================== 顶部页面切换 ====================
const activePage = ref('home')
const pageOptions = [
  { label: '首页', value: 'home' },
  { label: '资讯速览', value: 'news' },
  { label: '设置', value: 'settings' },
]

function onFilterChange({ games, owners, source, priority, resource, keyword, dateRange: dr }) {
  // 前端筛选（不触发 API）
  filterSource.value = source
  filterPriority.value = priority
  filterResource.value = resource
  dateRange.value = dr || null

  // 后端筛选（只有值真正变化时才触发 API）
  const gamesChanged = filterGames.value !== games
  const ownersChanged = filterOwners.value !== owners
  const keywordChanged = filterKeyword.value !== keyword

  filterGames.value = games
  filterOwners.value = owners
  filterKeyword.value = keyword

  if (gamesChanged || ownersChanged || keywordChanged) {
    loadData()
  }
}

// 前端筛选状态
const filterPriority = ref(null)    // null=不筛选，数组=多选
const filterSource = ref(null)      // null=不筛选，'news'/'event'
const filterResource = ref(null)    // null=不筛选，true/false

function applyFrontendFilters(items) {
  let filtered = items
  if (filterPriority.value && filterPriority.value.length) {
    filtered = filtered.filter(i => filterPriority.value.includes(i.priority))
  }
  if (filterSource.value !== null) {
    filtered = filtered.filter(i => i.source === filterSource.value)
  }
  if (filterResource.value !== null) {
    filtered = filtered.filter(i => i.resource_ready === filterResource.value)
  }
  if (dateRange.value && dateRange.value.length === 2) {
    filtered = filtered.filter(i => i.item_date >= dateRange.value[0] && i.item_date <= dateRange.value[1])
  }
  return filtered
}

const hasActiveFilter = computed(() => Boolean(
  filterGames.value ||
  filterOwners.value ||
  filterKeyword.value.trim() ||
  (filterPriority.value && filterPriority.value.length) ||
  filterSource.value !== null ||
  filterResource.value !== null ||
  (dateRange.value && dateRange.value.length === 2)
))

const filteredData = computed(() => applyFrontendFilters(calendarData.value))

const navigationItems = ref([])
const navigationLoading = ref(false)
const navigationLoaded = ref(false)
const navigationCacheKey = ref('')
const activeFilterDate = ref('')

const navigationRange = computed(() => {
  if (dateRange.value && dateRange.value.length === 2) {
    return { start: dateRange.value[0], end: dateRange.value[1] }
  }
  return {
    start: minMonth.format('YYYY-MM-DD'),
    end: maxMonth.endOf('month').format('YYYY-MM-DD'),
  }
})

const navigationQueryKey = computed(() => JSON.stringify({
  start: navigationRange.value.start,
  end: navigationRange.value.end,
  games: filterGames.value || '',
  owners: filterOwners.value || '',
  keyword: filterKeyword.value.trim(),
}))

const navigableDates = computed(() => {
  const visibleItems = applyFrontendFilters(navigationItems.value).filter(item => !item.hidden)
  return [...new Set(visibleItems.map(item => item.item_date))]
    .sort((a, b) => dayjs(a).valueOf() - dayjs(b).valueOf())
})

const activeFilterDateIndex = computed(() => {
  if (!activeFilterDate.value) return -1
  return navigableDates.value.indexOf(activeFilterDate.value)
})

const navigationAvailable = computed(() => !navigationLoaded.value || navigableDates.value.length > 0)
const canNavigatePrevDate = computed(() => activeFilterDateIndex.value > 0)
const canNavigateNextDate = computed(() => (
  activeFilterDateIndex.value >= 0 && activeFilterDateIndex.value < navigableDates.value.length - 1
))

function resetFilterNavigationState() {
  activeFilterDate.value = ''
  navigationItems.value = []
  navigationLoaded.value = false
  navigationCacheKey.value = ''
  navigationLoading.value = false
}

async function ensureNavigationItems(force = false) {
  if (!hasActiveFilter.value) {
    resetFilterNavigationState()
    return []
  }

  const cacheKey = navigationQueryKey.value
  if (!force && navigationLoaded.value && navigationCacheKey.value === cacheKey) {
    return navigationItems.value
  }

  navigationLoading.value = true
  try {
    const res = await fetchCalendar(navigationRange.value.start, navigationRange.value.end, {
      games: filterGames.value || undefined,
      owners: filterOwners.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    navigationItems.value = res.items || []
    navigationLoaded.value = true
    navigationCacheKey.value = cacheKey
    return navigationItems.value
  } catch (e) {
    console.error('加载筛选导航失败:', e)
    ElMessage.error('筛选定位失败，请稍后重试')
    return navigationItems.value
  } finally {
    navigationLoading.value = false
  }
}

function syncMonthToDate(dateStr) {
  if (!dateStr) return
  const visibleDates = new Set(days.value.map(day => day.date.format('YYYY-MM-DD')))
  if (visibleDates.has(dateStr)) return

  const targetDate = dayjs(dateStr)
  const targetMonth = targetDate.startOf('month')
  slideDirection.value = targetMonth.isAfter(currentDayjs.value) ? 'right' : 'left'
  currentYear.value = targetDate.year()
  currentMonth.value = targetDate.month() + 1
}

function focusFilterDate(dateStr) {
  if (!dateStr) {
    activeFilterDate.value = ''
    return
  }
  activeFilterDate.value = dateStr
  syncMonthToDate(dateStr)
}

async function onNavigateFilteredDate(direction) {
  if (!hasActiveFilter.value || navigationLoading.value) return

  await ensureNavigationItems()
  const dates = navigableDates.value

  if (!dates.length) {
    activeFilterDate.value = ''
    ElMessage.info('当前筛选下没有可定位的事项')
    return
  }

  if (!activeFilterDate.value) {
    focusFilterDate(dates[0])
    return
  }

  const currentIndex = dates.indexOf(activeFilterDate.value)
  if (currentIndex === -1) {
    focusFilterDate(dates[0])
    return
  }

  const nextIndex = direction === 'prev'
    ? Math.max(0, currentIndex - 1)
    : Math.min(dates.length - 1, currentIndex + 1)

  focusFilterDate(dates[nextIndex])
}

const dataByDate = computed(() => groupByDate(filteredData.value))

// ==================== 统计数据（支持日期范围） ====================
const rangeData = ref(null) // 日期范围请求的数据，null 时用当月数据

watch(dateRange, async (val) => {
  if (val && val.length === 2) {
    try {
      const res = await fetchCalendar(val[0], val[1], {
        games: filterGames.value || undefined,
        owners: filterOwners.value || undefined,
        keyword: filterKeyword.value || undefined,
      })
      rangeData.value = res.items || []
    } catch (e) {
      console.error('加载范围数据失败:', e)
      rangeData.value = null
    }
  } else {
    rangeData.value = null
  }
})

const statsSourceData = computed(() => {
  const source = rangeData.value !== null ? rangeData.value : calendarData.value
  return applyFrontendFilters(source)
})

// ==================== 月度统计 ====================
function buildStats(items) {
  const total = items.length
  const priority = { 3: 0, 2: 0, 1: 0, 0: 0 }
  const gameCount = {}
  const ownerCount = {}
  let newsCount = 0
  let eventCount = 0
  let configuredCount = 0
  let unconfiguredCount = 0
  for (const item of items) {
    if (item.source === 'news') newsCount++
    else eventCount++
    priority[item.priority] = (priority[item.priority] || 0) + 1
    gameCount[item.game] = (gameCount[item.game] || 0) + 1
    if (item.resource_ready) configuredCount++
    else unconfiguredCount++
    if (item.owners) {
      for (const o of item.owners) {
        ownerCount[o] = (ownerCount[o] || 0) + 1
      }
    }
  }
  return {
    total, newsCount, eventCount, priority,
    gameDist: Object.entries(gameCount).sort((a, b) => b[1] - a[1]),
    ownerDist: Object.entries(ownerCount).sort((a, b) => b[1] - a[1]),
    configuredCount, unconfiguredCount,
  }
}

const allStats = computed(() => {
  if (rangeData.value !== null) {
    return buildStats(statsSourceData.value.filter(i => !i.hidden))
  }
  const monthPrefix = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`
  return buildStats(statsSourceData.value.filter(i => !i.hidden && i.item_date.startsWith(monthPrefix)))
})

const keyStats = computed(() => {
  if (rangeData.value !== null) {
    return buildStats(statsSourceData.value.filter(i => !i.hidden && i.priority > 0))
  }
  const monthPrefix = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`
  return buildStats(statsSourceData.value.filter(i => !i.hidden && i.item_date.startsWith(monthPrefix) && i.priority > 0))
})

// 快速管理的数据源（和统计面板一致）
const quickManageItems = computed(() => {
  if (rangeData.value !== null) {
    return statsSourceData.value.filter(i => !i.hidden)
  }
  const monthPrefix = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`
  return filteredData.value.filter(i => !i.hidden && i.item_date.startsWith(monthPrefix))
})

async function loadData() {
  loading.value = true
  try {
    const first = days.value[0].date.format('YYYY-MM-DD')
    const last = days.value[days.value.length - 1].date.format('YYYY-MM-DD')
    const res = await fetchCalendar(first, last, {
      games: filterGames.value || undefined,
      owners: filterOwners.value || undefined,
      keyword: filterKeyword.value || undefined,
    })
    calendarData.value = res.items || []
  } catch (e) {
    console.error('加载日历数据失败:', e)
    ElMessage.error('加载数据失败，请刷新重试')
  } finally {
    loading.value = false
  }
}

async function loadGames() {
  try {
    const res = await fetchGames()
    gameOptions.value = res.games || []
  } catch (e) {
    console.error('加载游戏列表失败:', e)
  }
}

async function loadOwnerNames() {
  try {
    const res = await fetchOwnerNames()
    ownerOptions.value = res.owners || []
  } catch (e) {
    console.error('加载负责人列表失败:', e)
  }
}

// ==================== 资讯速览数据 ====================
const overviewItems = ref([])
const overviewLoading = ref(false)
const overviewLoaded = ref(false)
const overviewStale = ref(false)
const overviewReloadQueued = ref(false)

async function loadOverview(force = false) {
  if (overviewLoading.value) {
    if (force) overviewReloadQueued.value = true
    return
  }
  if (overviewLoaded.value && !overviewStale.value && !force) return

  overviewLoading.value = true
  try {
    const res = await fetchOverview()
    overviewItems.value = res.items || []
    overviewLoaded.value = true
    overviewStale.value = false
  } catch (e) {
    console.error('加载资讯速览失败:', e)
    ElMessage.error('资讯速览加载失败')
  } finally {
    overviewLoading.value = false
    if (overviewReloadQueued.value) {
      overviewReloadQueued.value = false
      await loadOverview(true)
    }
  }
}

function markOverviewStale(refreshIfVisible = true) {
  overviewStale.value = true
  if (refreshIfVisible && activePage.value === 'news') {
    void loadOverview(true)
  }
}

watch([currentYear, currentMonth], loadData)

watch(activePage, (page) => {
  if (page === 'news') loadOverview()
})

watch(hasActiveFilter, (active) => {
  if (!active) {
    resetFilterNavigationState()
  }
})

watch(navigationQueryKey, async (_newKey, oldKey) => {
  if (!oldKey || !hasActiveFilter.value) return
  if (!navigationLoaded.value && !activeFilterDate.value) return
  await ensureNavigationItems(true)
})

watch(navigableDates, (dates) => {
  if (!activeFilterDate.value) return
  if (!dates.length) {
    activeFilterDate.value = ''
    return
  }
  if (!dates.includes(activeFilterDate.value)) {
    focusFilterDate(dates[0])
  }
})

// ==================== 日期详情侧栏 ====================
const detailVisible = ref(false)
const selectedDate = ref('')

const selectedItems = computed(() => dataByDate.value[selectedDate.value] || [])

function onSelectDate(dateStr) {
  selectedDate.value = dateStr
  detailVisible.value = true
}

// ==================== 就地更新工具 ====================
function updateItemInList(list, source, id, updates) {
  const idx = list.findIndex(i => i.source === source && i.id === id)
  if (idx === -1) return list
  const next = [...list]
  next[idx] = { ...next[idx], ...updates }
  return next
}

function updateItemInPlace(source, id, updates) {
  calendarData.value = updateItemInList(calendarData.value, source, id, updates)
  if (rangeData.value !== null) {
    rangeData.value = updateItemInList(rangeData.value, source, id, updates)
  }
  if (navigationItems.value.length) {
    navigationItems.value = updateItemInList(navigationItems.value, source, id, updates)
  }
  if (overviewLoaded.value || overviewItems.value.length) {
    overviewItems.value = updateItemInList(overviewItems.value, source, id, updates)
  }
  markOverviewStale()
}

function removeItemInPlace(source, id) {
  calendarData.value = calendarData.value.filter(i => !(i.source === source && i.id === id))
  if (rangeData.value !== null) {
    rangeData.value = rangeData.value.filter(i => !(i.source === source && i.id === id))
  }
  if (navigationItems.value.length) {
    navigationItems.value = navigationItems.value.filter(i => !(i.source === source && i.id === id))
  }
  if (overviewLoaded.value || overviewItems.value.length) {
    overviewItems.value = overviewItems.value.filter(i => !(i.source === source && i.id === id))
  }
  markOverviewStale()
}

function addItemInPlace(item) {
  calendarData.value.push(item)
  if (rangeData.value !== null && dateRange.value?.length === 2 && item.item_date >= dateRange.value[0] && item.item_date <= dateRange.value[1]) {
    rangeData.value = [...rangeData.value, item]
  }
  markOverviewStale()
}

const pendingActionMap = ref({})

function isActionPending(key) {
  return Boolean(pendingActionMap.value[key])
}

function setActionPending(key, pending) {
  const nextMap = { ...pendingActionMap.value }
  if (pending) nextMap[key] = true
  else delete nextMap[key]
  pendingActionMap.value = nextMap
}

async function runLockedAction(key, action) {
  if (isActionPending(key)) return null
  setActionPending(key, true)
  try {
    return await action()
  } finally {
    setActionPending(key, false)
  }
}

function getItemActionKey(action, item) {
  return `${action}:${item.source}:${item.id}`
}

function isItemActionPending(action, item) {
  return isActionPending(getItemActionKey(action, item))
}

const annotationSaving = computed(() => isActionPending('annotation-save'))
const eventSaving = computed(() => isActionPending('event-save'))
const addGameSaving = computed(() => isActionPending('event-add-game'))

// ==================== 标注编辑 ====================
const annotationFormVisible = ref(false)
const annotationTarget = ref(null)

function onEditAnnotation(item) {
  if (!requireAdminAction()) return
  annotationTarget.value = item
  annotationFormVisible.value = true
}

async function onSaveAnnotation(formData) {
  if (!requireAdminAction()) return
  if (!annotationTarget.value) return
  await runLockedAction('annotation-save', async () => {
    try {
      await updateAnnotation(annotationTarget.value.id, formData)
      updateItemInPlace('news', annotationTarget.value.id, {
        priority: formData.priority,
        alias: formData.alias,
        resource_ready: formData.resource_ready,
      })
      annotationFormVisible.value = false
      ElMessage.success('备注已保存')
    } catch (e) {
      ElMessage.error('更新失败: ' + e.message)
    }
  })
}

// ==================== 快捷操作：优先级 ====================
async function onQuickPriority({ item, priority }) {
  if (!requireAdminAction()) return
  await runLockedAction(getItemActionKey('priority', item), async () => {
    try {
      if (item.source === 'news') {
        await updateAnnotation(item.id, { priority })
      } else {
        await updateEvent(item.id, { priority })
      }
      updateItemInPlace(item.source, item.id, { priority })
    } catch (e) {
      ElMessage.error('更新失败: ' + e.message)
    }
  })
}

// ==================== 快捷操作：资源位 ====================
async function onQuickResource({ item, resource_ready }) {
  if (!requireAdminAction()) return
  await runLockedAction(getItemActionKey('resource', item), async () => {
    try {
      if (item.source === 'news') {
        await updateAnnotation(item.id, { resource_ready })
      } else {
        await updateEvent(item.id, { resource_ready })
      }
      updateItemInPlace(item.source, item.id, { resource_ready })
    } catch (e) {
      ElMessage.error('更新失败: ' + e.message)
    }
  })
}

// ==================== 隐藏 / 恢复 ====================
async function onHideNews(item) {
  if (!requireAdminAction()) return
  await runLockedAction(getItemActionKey('hide', item), async () => {
    try {
      await updateAnnotation(item.id, { hidden: true })
      updateItemInPlace('news', item.id, { hidden: true })
      ElMessage.success('已隐藏')
    } catch (e) {
      ElMessage.error('隐藏失败: ' + e.message)
    }
  })
}

async function onRestoreNews(item) {
  if (!requireAdminAction()) return
  await runLockedAction(getItemActionKey('restore', item), async () => {
    try {
      await updateAnnotation(item.id, { hidden: false })
      updateItemInPlace('news', item.id, { hidden: false })
      ElMessage.success('已恢复显示')
    } catch (e) {
      ElMessage.error('恢复失败: ' + e.message)
    }
  })
}

function onRestoreItem(item) {
  updateItemInPlace('news', item.id, { hidden: false })
}

// ==================== 自定义事件 ====================
const eventFormVisible = ref(false)
const eventTarget = ref(null)

function onNewEvent() {
  if (!requireAdminAction()) return
  eventTarget.value = null
  selectedDate.value = ''
  eventFormVisible.value = true
}

// 从日历单元格或侧栏触发的添加事项（带日期）
function onAddEventForDate(dateStr) {
  if (!requireAdminAction()) return
  eventTarget.value = null
  selectedDate.value = dateStr
  eventFormVisible.value = true
}

function onEditEvent(item) {
  if (!requireAdminAction()) return
  eventTarget.value = item
  eventFormVisible.value = true
}

async function onSaveEvent(formData) {
  if (!requireAdminAction()) return
  await runLockedAction('event-save', async () => {
    try {
      if (formData.id) {
        const res = await updateEvent(formData.id, {
          description: formData.description,
          event_date: formData.event_date,
          priority: formData.priority,
          resource_ready: formData.resource_ready,
        })
        updateItemInPlace('event', formData.id, {
          title: res.description,
          item_date: res.event_date,
          priority: res.priority,
          resource_ready: res.resource_ready,
        })
        ElMessage.success('事件已更新')
      } else {
        const res = await createEvent({
          game: formData.game,
          description: formData.description,
          event_date: formData.event_date,
          priority: formData.priority,
          resource_ready: formData.resource_ready,
          alias: '',
        })
        addItemInPlace({
          id: res.id,
          source: 'event',
          game: res.game,
          title: res.description,
          link: '',
          item_date: res.event_date,
          priority: res.priority,
          alias: '',
          resource_ready: res.resource_ready,
          hidden: false,
          owners: [],
        })
        ElMessage.success('事件已创建')
        // 脉冲高亮对应日期格
        pulseDate(res.event_date)
      }
      eventFormVisible.value = false
    } catch (e) {
      ElMessage.error('保存失败，请重试')
    }
  })
}

// 日期格脉冲高亮
function pulseDate(dateStr) {
  nextTick(() => {
    const cell = document.querySelector(`[role="gridcell"][data-date="${dateStr}"]`)
    if (!cell) return
    cell.classList.add('cell-pulse')
    cell.addEventListener('animationend', () => cell.classList.remove('cell-pulse'), { once: true })
  })
}

async function onDeleteEvent(item) {
  if (!requireAdminAction()) return
  await runLockedAction(getItemActionKey('delete', item), async () => {
    try {
      await apiDeleteEvent(item.id)
      removeItemInPlace('event', item.id)
      ElMessage.success('事件已删除')
    } catch (e) {
      ElMessage.error('删除失败，请重试')
    }
  })
}

// ==================== 添加新游戏 ====================
async function onAddGame({ game, owners }) {
  if (!requireAdminAction()) return
  await runLockedAction('event-add-game', async () => {
    try {
      await createOwner({ game, owners: owners || [] })
      if (!gameOptions.value.includes(game)) {
        gameOptions.value.push(game)
        gameOptions.value.sort()
      }
      ElMessage.success(`已添加游戏: ${game}`)
    } catch (e) {
      if (!e.message.includes('409') && !e.message.includes('已存在')) {
        ElMessage.error('添加失败: ' + e.message)
      }
    }
  })
}

// ==================== 管理员登录 ====================
const logoutDialogVisible = ref(false)

async function onAdminLogin(password) {
  try {
    await login(password)
  } catch (e) {
    ElMessage.error(e.message || '登录失败')
  }
}

function onEnterAdminMode() {
  if (!isAdmin.value) openLoginDialog()
}

async function onConfirmLogout() {
  await logout()
  logoutDialogVisible.value = false
}

// ==================== 数据管理彩蛋（PC端 + 已登录 + 连击 logo 6 次） ====================
const logoClickTimes = ref([])

function onLogoClick() {
  // 仅 PC 端触发（非触摸设备）
  const isTouchDevice = window.matchMedia('(hover: none) and (pointer: coarse)').matches
  if (isTouchDevice) return
  // 仅已登录管理员
  if (!isAdmin.value) return

  const now = Date.now()
  logoClickTimes.value.push(now)
  // 只保留最近 6 次
  if (logoClickTimes.value.length > 6) logoClickTimes.value.shift()
  // 检查 6 次点击是否在 2 秒内
  if (logoClickTimes.value.length === 6) {
    const span = logoClickTimes.value[5] - logoClickTimes.value[0]
    if (span <= 2000) {
      logoClickTimes.value = []
      window.open('/dbadmin.html', '_blank')
    }
  }
}

// ==================== 统计切换 ====================
const statsView = ref('all') // 'all' | 'key'
const statsExpanded = ref(false)

// 移动端左右滑动切换统计视图
let statsTouchStartX = 0
let statsTouchStartY = 0
function onStatsTouchStart(e) {
  statsTouchStartX = e.touches[0].clientX
  statsTouchStartY = e.touches[0].clientY
}
function onStatsTouchEnd(e) {
  const dx = e.changedTouches[0].clientX - statsTouchStartX
  const dy = Math.abs(e.changedTouches[0].clientY - statsTouchStartY)
  const absDx = Math.abs(dx)
  if (absDx > 60 && absDx > dy * 1.2) {
    statsView.value = dx < 0 ? 'key' : 'all'
  }
}

// ==================== 移动端底部悬浮栏 ====================
const topBarRef = ref(null)
const showBottomBar = ref(false)

onMounted(() => {
  Promise.all([refreshAuthStatus(), loadGames(), loadOwnerNames(), loadData()])

  // 监听顶部切换区域是否滚出视口
  nextTick(() => {
    if (!topBarRef.value) return
    const observer = new IntersectionObserver(
      ([entry]) => { showBottomBar.value = !entry.isIntersecting },
      { threshold: 0 }
    )
    observer.observe(topBarRef.value)
  })
})
</script>

<template>
  <ElConfigProvider :locale="elLocale">
  <main class="max-w-7xl mx-auto px-4 md:px-6 pt-6 md:pt-8 pb-24 md:pb-12">
    <!-- 顶部标题区 -->
    <div class="app-header flex items-center justify-between mb-6 md:mb-8">
      <img src="./assets/banner_title.png" alt="START 游戏日历" class="app-title-logo h-auto max-h-6 md:max-h-11" style="width: auto; display: block; cursor: default" fetchpriority="high" width="300" height="44" @click="onLogoClick" />
      <div class="auth-control-group">
        <div class="flex items-center gap-2">
          <div class="auth-mode-switch" aria-label="权限模式">
            <button
              type="button"
              class="auth-mode-button"
              :class="{ active: !isAdmin }"
              :disabled="authLoading"
              @click="isAdmin && (logoutDialogVisible = true)"
            >浏览</button>
            <button
              type="button"
              class="auth-mode-button"
              :class="{ active: isAdmin }"
              :disabled="authLoading"
              @click="onEnterAdminMode"
            >管理</button>
          </div>
          <el-button type="primary" :disabled="!isAdmin" @click="onNewEvent">
            <el-icon class="md:mr-1"><Plus /></el-icon>
            <span class="hidden md:inline">新建事件</span>
          </el-button>
        </div>
        <p v-if="!isAdmin" class="auth-mode-hint">浏览模式下仅可查看日历</p>
      </div>
    </div>

    <!-- 顶部页面切换 -->
    <div ref="topBarRef" class="mb-6 md:mb-8 flex justify-center md:justify-start">
      <TopSegmentSwitch v-model="activePage" :options="pageOptions" />
    </div>

    <div v-show="activePage === 'home'">
    <!-- 筛选栏 -->
    <div class="mb-6 md:mb-8 p-3 md:p-4" style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px">
      <FilterBar
        :game-options="gameOptions"
        :owner-options="ownerOptions"
        :navigation-started="Boolean(activeFilterDate)"
        :navigation-busy="navigationLoading"
        :navigation-available="navigationAvailable"
        :can-navigate-prev="canNavigatePrevDate"
        :can-navigate-next="canNavigateNextDate"
        @filter-change="onFilterChange"
        @navigate-filter-date="onNavigateFilteredDate"
      />
    </div>

    <!-- 月份导航 -->
    <div class="flex items-center justify-center md:justify-start gap-2 md:gap-3 mb-3 md:mb-4">
      <el-button class="month-nav-button pill-press" size="small" :disabled="!canPrev" @click="prevMonth">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <span class="text-sm md:text-base" style="font-weight: 600; color: #111; min-width: 100px; text-align: center; display: inline-block; font-variant-numeric: tabular-nums">
        {{ monthLabel }}
      </span>
      <el-button class="month-nav-button pill-press" size="small" :disabled="!canNext" @click="nextMonth">
        <el-icon><ArrowRight /></el-icon>
      </el-button>
      <el-button size="small" type="primary" plain @click="goToday">今天</el-button>
    </div>

    <!-- 日历网格 — 主体区域 -->
    <div
      v-loading="loading"
      :key="`${currentYear}-${currentMonth}`"
      :class="slideDirection === 'left' ? 'calendar-slide-left' : 'calendar-slide-right'"
      style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden"
    >
      <CalendarGrid
        :days="days"
        :data-by-date="dataByDate"
        :selected-date="activeFilterDate"
        :can-edit="isAdmin"
        @select-date="onSelectDate"
        @add-event="onAddEventForDate"
        @prev-month="prevMonth"
        @next-month="nextMonth"
      />
    </div>

    <!-- 事件统计 -->
    <div class="mt-6 md:mt-10">
      <div class="stats-enter p-4 md:py-5 md:px-6" style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-1.5">
            <button
              class="px-3 py-1 text-xs rounded-md border pill-press cursor-pointer"
              :style="statsView === 'all'
                ? { background: '#111', color: '#fff', borderColor: '#111' }
                : { background: '#fff', color: '#999', borderColor: '#e5e5e5' }"
              @click="statsView = 'all'"
            >全部事件</button>
            <button
              class="px-3 py-1 text-xs rounded-md border pill-press cursor-pointer"
              :style="statsView === 'key'
                ? { background: '#111', color: '#fff', borderColor: '#111' }
                : { background: '#fff', color: '#999', borderColor: '#e5e5e5' }"
              @click="statsView = 'key'"
            >重点事件</button>
            <!-- 收缩时显示总条数 -->
            <span v-if="!statsExpanded" style="font-size: 0.8125rem; color: #999; margin-left: 8px; font-variant-numeric: tabular-nums">
              {{ statsView === 'all' ? allStats.total : keyStats.total }} 条
            </span>
          </div>
          <!-- 展开/收缩按钮 -->
          <button
            class="pill-press cursor-pointer"
            style="background: none; border: none; padding: 4px; color: #999; transition: transform 200ms"
            :style="{ transform: statsExpanded ? 'rotate(180deg)' : 'rotate(0deg)' }"
            @click="statsExpanded = !statsExpanded"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
        <!-- 展开时显示详细统计 -->
        <div
          v-if="statsExpanded"
          style="margin-top: 16px"
          @touchstart.passive="onStatsTouchStart"
          @touchend.passive="onStatsTouchEnd"
        >
          <StatsCard
            v-if="statsView === 'all'"
            title="全部事件"
            :stats="allStats"
          />
          <StatsCard
            v-else
            title="重点事件"
            subtitle="仅高/中/低优先级"
            :stats="keyStats"
          />
        </div>
      </div>
    </div>

    <!-- 快速管理 -->
    <div class="mt-6 md:mt-10">
      <div class="p-4 md:py-5 md:px-6" style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px">
        <QuickManage
          :items="quickManageItems"
          :can-edit="isAdmin"
          :is-item-action-pending="isItemActionPending"
          @edit-annotation="onEditAnnotation"
          @hide-news="onHideNews"
          @edit-event="onEditEvent"
          @delete-event="onDeleteEvent"
          @add-event="onAddEventForDate"
          @quick-priority="onQuickPriority"
          @quick-resource="onQuickResource"
        />
      </div>
    </div>
    </div>

    <NewsOverview
      v-show="activePage === 'news'"
      :items="overviewItems"
      :loading="overviewLoading"
      :can-edit="isAdmin"
      :is-item-action-pending="isItemActionPending"
      @refresh="loadOverview(true)"
      @edit-annotation="onEditAnnotation"
      @hide-news="onHideNews"
      @edit-event="onEditEvent"
      @delete-event="onDeleteEvent"
      @quick-priority="onQuickPriority"
      @quick-resource="onQuickResource"
    />

    <!-- 日期详情侧栏 -->
    <DayDetail
      :visible="detailVisible"
      :date="selectedDate"
      :items="selectedItems"
      :can-edit="isAdmin"
      :is-item-action-pending="isItemActionPending"
      @close="detailVisible = false"
      @edit-annotation="onEditAnnotation"
      @hide-news="onHideNews"
      @restore-news="onRestoreNews"
      @edit-event="onEditEvent"
      @delete-event="onDeleteEvent"
      @add-event="onAddEventForDate"
      @quick-priority="onQuickPriority"
      @quick-resource="onQuickResource"
    />

    <!-- 标注编辑弹窗（仅爬虫数据，含事件备注） -->
    <AnnotationForm
      :visible="annotationFormVisible"
      :item="annotationTarget"
      :saving="annotationSaving"
      @close="annotationFormVisible = false"
      @save="onSaveAnnotation"
    />

    <!-- 事件新建/编辑弹窗 -->
    <EventForm
      :visible="eventFormVisible"
      :event="eventTarget"
      :game-options="gameOptions"
      :default-date="selectedDate"
      :saving="eventSaving"
      :adding-game="addGameSaving"
      @close="eventFormVisible = false"
      @save="onSaveEvent"
      @add-game="onAddGame"
    />

    <SettingsPage
      v-show="activePage === 'settings'"
      :active="activePage === 'settings'"
      :can-edit="isAdmin"
      @restore-item="onRestoreItem"
    />

    <AdminLoginDialog
      v-model:visible="loginDialogVisible"
      :loading="authLoading"
      @login="onAdminLogin"
    />

    <el-dialog
      v-model="logoutDialogVisible"
      title="退出管理模式"
      width="320px"
      class="admin-logout-dialog"
      append-to-body
      :close-on-click-modal="!authLoading"
      :close-on-press-escape="!authLoading"
    >
      <p class="admin-logout-desc">退出后将无法编辑日历。</p>
      <template #footer>
        <el-button :disabled="authLoading" @click="logoutDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="authLoading" @click="onConfirmLogout">退出</el-button>
      </template>
    </el-dialog>
  </main>

  <!-- 移动端底部悬浮栏（顶部切换区域滚出视口时显示） -->
  <div
    class="mobile-bottom-bar md:hidden"
    :class="{ visible: showBottomBar && !detailVisible }"
  >
    <TopSegmentSwitch v-model="activePage" :options="pageOptions" />
    <button class="bottom-add-btn" :disabled="!isAdmin" @click="onNewEvent">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
        <path d="M12 5v14M5 12h14"/>
      </svg>
    </button>
  </div>

  </ElConfigProvider>
</template>

<style scoped>
:global(.admin-logout-dialog) {
  width: min(320px, calc(100vw - 64px)) !important;
}

.admin-logout-desc {
  margin: 0;
  color: #888;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.app-title-logo {
  min-width: 0;
  flex-shrink: 1;
}

.auth-control-group {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.auth-mode-hint {
  margin: 0;
  color: #999;
  font-size: 0.6875rem;
  line-height: 1.2;
  white-space: nowrap;
}

.auth-mode-switch {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}

.auth-mode-button {
  min-height: 28px;
  padding: 0 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #999;
  font-size: 0.8125rem;
  line-height: 1;
  cursor: pointer;
  transition: background-color 150ms ease, color 150ms ease, opacity 150ms ease;
}

.auth-mode-button.active {
  background: #111;
  color: #fff;
}

.auth-mode-button:disabled {
  cursor: default;
  opacity: 0.55;
}

.auth-mode-button:not(:disabled):not(.active):hover {
  background: #f5f5f5;
  color: #555;
}

@media (max-width: 767px) {
  .app-header {
    align-items: center;
    gap: 8px;
  }

  .app-title-logo {
    max-width: clamp(132px, 46vw, 160px);
  }

  .auth-control-group > .flex {
    max-width: 48vw;
  }

  .auth-control-group {
    flex: 0 0 auto;
    gap: 3px;
  }

  .auth-mode-hint {
    max-width: 48vw;
    overflow: hidden;
    font-size: 0.625rem;
    text-overflow: ellipsis;
    transform: translateY(-1px);
  }

  .auth-mode-button {
    min-height: 30px;
    padding: 0 8px;
    font-size: 0.75rem;
  }
}

/* ===== 移动端底部悬浮栏 ===== */
.mobile-bottom-bar {
  position: fixed;
  bottom: calc(28px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%) translateY(calc(100% + 40px));
  display: flex;
  align-items: center;
  gap: 10px;
  transition: transform 250ms cubic-bezier(0.25, 1, 0.5, 1);
  z-index: 100;
  pointer-events: none;
}

@media (min-width: 768px) {
  .mobile-bottom-bar {
    display: none !important;
  }
}

.mobile-bottom-bar.visible {
  transform: translateX(-50%) translateY(0);
  pointer-events: auto;
}

/* 底部栏里的 pill 加大尺寸 */
.mobile-bottom-bar :deep(.top-segment-switch) {
  width: auto;
  min-width: 260px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.12);
}

.mobile-bottom-bar :deep(.top-segment-item) {
  height: 44px;
  font-size: 0.875rem;
  padding: 0 20px;
  white-space: nowrap;
}

.bottom-add-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 0;
  border-radius: 50%;
  background: #111;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  transition: opacity 150ms, transform 150ms;
}

.bottom-add-btn:active {
  transform: scale(0.9);
}

.bottom-add-btn:disabled {
  background: #ccc;
  cursor: default;
  box-shadow: none;
}
</style>
