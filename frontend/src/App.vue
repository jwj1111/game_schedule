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

// 懒加载：非首屏关键组件（弹窗/侧栏，用户交互后才需要）
const DayDetail = defineAsyncComponent(() => import('./components/DayDetail.vue'))
const AnnotationForm = defineAsyncComponent(() => import('./components/AnnotationForm.vue'))
const EventForm = defineAsyncComponent(() => import('./components/EventForm.vue'))
import {
  fetchCalendar, fetchGames, fetchOwnerNames,
  updateAnnotation,
  createEvent, updateEvent, deleteEvent as apiDeleteEvent,
  createOwner,
} from './api/index.js'
import { generateMonthGrid, groupByDate } from './utils/calendar.js'

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

watch([currentYear, currentMonth], loadData)

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

onMounted(() => { Promise.all([loadGames(), loadOwnerNames(), loadData()]) })

// ==================== 日期详情侧栏 ====================
const detailVisible = ref(false)
const selectedDate = ref('')

const selectedItems = computed(() => dataByDate.value[selectedDate.value] || [])

function onSelectDate(dateStr) {
  selectedDate.value = dateStr
  detailVisible.value = true
}

// ==================== 就地更新工具 ====================
function updateItemInPlace(source, id, updates) {
  const idx = calendarData.value.findIndex(i => i.source === source && i.id === id)
  if (idx !== -1) {
    calendarData.value[idx] = { ...calendarData.value[idx], ...updates }
  }
}

function removeItemInPlace(source, id) {
  calendarData.value = calendarData.value.filter(i => !(i.source === source && i.id === id))
}

function addItemInPlace(item) {
  calendarData.value.push(item)
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
  annotationTarget.value = item
  annotationFormVisible.value = true
}

async function onSaveAnnotation(formData) {
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
  eventTarget.value = null
  selectedDate.value = ''
  eventFormVisible.value = true
}

// 从日历单元格或侧栏触发的添加事项（带日期）
function onAddEventForDate(dateStr) {
  eventTarget.value = null
  selectedDate.value = dateStr
  eventFormVisible.value = true
}

function onEditEvent(item) {
  eventTarget.value = item
  eventFormVisible.value = true
}

async function onSaveEvent(formData) {
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
    const cells = document.querySelectorAll('[role="gridcell"]')
    for (const cell of cells) {
      if (cell.textContent.trim().startsWith(String(parseInt(dateStr.split('-')[2])))) {
        cell.classList.add('cell-pulse')
        cell.addEventListener('animationend', () => cell.classList.remove('cell-pulse'), { once: true })
        break
      }
    }
  })
}

async function onDeleteEvent(item) {
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

// ==================== 顶部页面切换 ====================
const activePage = ref('home')
const pageOptions = [
  { label: '首页', value: 'home' },
  { label: '资讯速览', value: 'news' },
  { label: '设置', value: 'settings' },
]

// ==================== 统计切换 ====================
const statsView = ref('all') // 'all' | 'key'
const statsExpanded = ref(true)
</script>

<template>
  <ElConfigProvider :locale="elLocale">
  <main class="max-w-7xl mx-auto px-4 md:px-6 pt-6 md:pt-8 pb-12">
    <!-- 顶部标题区 -->
    <div class="flex items-center justify-between mb-6 md:mb-8">
      <img src="./assets/banner_title.png" alt="START 游戏日历" class="h-auto max-h-6 md:max-h-11" style="width: auto; display: block" fetchpriority="high" width="300" height="44" />
      <div class="flex gap-2">
        <el-button type="primary" @click="onNewEvent">
          <el-icon class="md:mr-1"><Plus /></el-icon>
          <span class="hidden md:inline">新建事件</span>
        </el-button>
      </div>
    </div>

    <!-- 顶部页面切换 -->
    <div class="mb-6 md:mb-8 flex justify-center md:justify-start">
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
        @select-date="onSelectDate"
        @add-event="onAddEventForDate"
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
        <div v-if="statsExpanded" style="margin-top: 16px">
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

    <section v-show="activePage === 'news'" class="p-6 md:p-8" style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; min-height: 320px">
        <div class="mx-auto flex flex-col items-center justify-center text-center" style="min-height: 260px; max-width: 360px">
          <div style="font-size: 0.875rem; font-weight: 600; color: #111; margin-bottom: 6px">资讯速览</div>
          <div style="font-size: 0.8125rem; color: #999; line-height: 1.6">
            页面已预留，后续可在这里承载资讯列表、重点摘要和快速处理入口。
          </div>
        </div>
    </section>

    <!-- 日期详情侧栏 -->
    <DayDetail
      :visible="detailVisible"
      :date="selectedDate"
      :items="selectedItems"
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
      @restore-item="onRestoreItem"
    />
  </main>
  </ElConfigProvider>
</template>
