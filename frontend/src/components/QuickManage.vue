<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'edit-annotation', 'hide-news', 'restore-news',
  'edit-event', 'delete-event', 'add-event',
  'quick-priority', 'quick-resource',
])

const priorityOptions = [
  { value: 3, label: '高', bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
  { value: 2, label: '中', bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
  { value: 1, label: '低', bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
  { value: 0, label: '无', bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-300' },
]

const expanded = ref(true)

// 从 items 中提取有数据的日期，去重排序
const availableDates = computed(() => {
  const dates = new Set()
  for (const item of props.items) {
    if (!item.hidden) dates.add(item.item_date)
  }
  return [...dates].sort()
})

const selectedDate = ref('')
const cachedOrder = ref([])
const groupedGames = ref([])

// items/筛选变化时，日期列表真正变化才重置到最早日期
let lastDatesKey = ''
watch(availableDates, (dates) => {
  const key = dates.join(',')
  if (key !== lastDatesKey) {
    lastDatesKey = key
    selectedDate.value = dates.length ? dates[0] : ''
  }
}, { immediate: true })

// 构建排序快照
function buildGroups(items) {
  const map = {}
  for (const item of items) {
    if (!map[item.game]) map[item.game] = []
    map[item.game].push(item)
  }
  const groups = Object.entries(map).map(([game, gameItems]) => ({
    game,
    itemIds: gameItems.sort((a, b) => b.priority - a.priority).map(i => `${i.source}-${i.id}`),
    maxPriority: Math.max(...gameItems.map(i => i.priority)),
  }))
  groups.sort((a, b) => b.maxPriority - a.maxPriority)
  return groups
}

function syncItems() {
  const dayData = props.items.filter(i => i.item_date === selectedDate.value && !i.hidden)
  const itemMap = {}
  for (const item of dayData) {
    itemMap[`${item.source}-${item.id}`] = item
  }

  const result = []
  for (const group of cachedOrder.value) {
    const items = group.itemIds
      .map(id => itemMap[id])
      .filter(i => i && !i.hidden)
    if (items.length) {
      result.push({ game: group.game, items })
    }
  }

  // 新增的事项
  const knownIds = new Set(cachedOrder.value.flatMap(g => g.itemIds))
  const newItems = dayData.filter(i => !knownIds.has(`${i.source}-${i.id}`))
  if (newItems.length) {
    for (const item of newItems) {
      const existing = result.find(g => g.game === item.game)
      if (existing) {
        existing.items.push(item)
      } else {
        result.push({ game: item.game, items: [item] })
      }
    }
    cachedOrder.value = buildGroups(dayData)
  }

  groupedGames.value = result
}

// 切换日期时重新排序
watch(selectedDate, (date) => {
  if (!date) {
    cachedOrder.value = []
    groupedGames.value = []
    return
  }
  const dayData = props.items.filter(i => i.item_date === date && !i.hidden)
  cachedOrder.value = buildGroups(dayData)
  syncItems()
})

// items 变化时就地更新，不重排
watch(() => props.items, () => {
  if (selectedDate.value) {
    syncItems()
  }
}, { deep: true })

// 格式化日期显示：4/29 周二
function formatDatePill(dateStr) {
  const d = new Date(dateStr)
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}/${d.getDate()} ${weekdays[d.getDay()]}`
}

// 当前日期事件数
function getDateCount(dateStr) {
  return props.items.filter(i => i.item_date === dateStr && !i.hidden).length
}

function onPriorityChange(item, newPriority) {
  emit('quick-priority', { item, priority: newPriority })
}
function onResourceToggle(item) {
  emit('quick-resource', { item, resource_ready: !item.resource_ready })
}

function scrollToDate(date) {
  selectedDate.value = date
}

const pillsRef = ref(null)

function scrollPills(direction) {
  if (!pillsRef.value) return
  const scrollAmount = pillsRef.value.clientWidth * 0.7
  pillsRef.value.scrollBy({ left: direction * scrollAmount, behavior: 'smooth' })
}
</script>

<template>
  <div>
    <!-- 头部：标题 + 展开/收缩 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span style="font-weight: 600; font-size: 0.9375rem; color: #111">快速管理</span>
        <span v-if="!expanded" style="font-size: 0.8125rem; color: #999; font-variant-numeric: tabular-nums">
          {{ availableDates.length }} 天 · {{ items.filter(i => !i.hidden).length }} 条
        </span>
      </div>
      <button
        class="pill-press cursor-pointer"
        style="background: none; border: none; padding: 4px; color: #999; transition: transform 200ms"
        :style="{ transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }"
        @click="expanded = !expanded"
      >
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>

    <template v-if="expanded">
      <!-- 无数据 -->
      <div v-if="!availableDates.length" style="text-align: center; padding: 32px 0">
        <div style="color: #ccc; font-size: 0.8125rem">当前筛选条件下没有事件</div>
      </div>

      <template v-else>
        <!-- 横向日期 pills -->
        <div class="flex items-center gap-1.5" style="margin-top: 12px">
          <!-- PC 左箭头 -->
          <button
            class="hidden md:flex items-center justify-center pill-press cursor-pointer"
            style="background: none; border: 1px solid #e5e5e5; border-radius: 6px; width: 28px; height: 28px; flex-shrink: 0; color: #999"
            @click="scrollPills(-1)"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M7.5 2.5L4 6L7.5 9.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>

          <!-- pills 容器 -->
          <div ref="pillsRef" class="date-pills">
            <button
              v-for="date in availableDates"
              :key="date"
              class="date-pill pill-press"
              :class="{ active: date === selectedDate }"
              @click="scrollToDate(date)"
            >
              <span class="date-pill-label">{{ formatDatePill(date) }}</span>
              <span class="date-pill-count">{{ getDateCount(date) }}</span>
            </button>
          </div>

          <!-- PC 右箭头 -->
          <button
            class="hidden md:flex items-center justify-center pill-press cursor-pointer"
            style="background: none; border: 1px solid #e5e5e5; border-radius: 6px; width: 28px; height: 28px; flex-shrink: 0; color: #999"
            @click="scrollPills(1)"
          >
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </button>
        </div>

        <!-- 事件列表 -->
        <div style="margin-top: 16px">
          <div v-for="group in groupedGames" :key="group.game" style="margin-bottom: 20px">
            <div style="font-size: 0.8125rem; font-weight: 600; color: #111; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; line-height: 1.3">
              {{ group.game }}
              <span style="font-size: 0.6875rem; color: #999; font-weight: 400; font-variant-numeric: tabular-nums">({{ group.items.length }})</span>
            </div>

            <div style="display: flex; flex-direction: column; gap: 8px; padding-left: 10px; border-left: 2px solid #e5e5e5">
              <div
                v-for="item in group.items"
                :key="`${item.source}-${item.id}`"
                style="padding: 10px 14px; border-radius: 6px; background: #fafafa"
              >
                <p style="font-size: 0.8125rem; color: #111; margin: 0 0 8px 0; line-height: 1.5">
                  {{ item.alias || item.title }}
                </p>
                <p v-if="item.alias && item.source === 'news'" style="font-size: 0.6875rem; color: #ccc; margin: 0 0 6px 0; line-height: 1.4">
                  原标题：{{ item.title }}
                </p>

                <!-- 快捷操作 -->
                <div class="flex items-center gap-4 flex-wrap" style="margin-bottom: 8px">
                  <div class="flex items-center gap-1.5">
                    <span style="font-size: 0.6875rem; color: #999">优先级</span>
                    <div class="flex gap-0.5">
                      <button
                        v-for="opt in priorityOptions"
                        :key="opt.value"
                        class="px-2 py-0.5 text-xs rounded border transition-colors cursor-pointer"
                        :class="item.priority === opt.value ? [opt.bg, opt.text, opt.border] : ''"
                        :style="item.priority !== opt.value ? { background: '#fff', borderColor: '#e5e5e5', color: '#ccc' } : {}"
                        @click="onPriorityChange(item, opt.value)"
                      >{{ opt.label }}</button>
                    </div>
                  </div>
                  <div class="flex items-center gap-1.5">
                    <span style="font-size: 0.6875rem; color: #999">资源位</span>
                    <el-switch
                      :model-value="item.resource_ready"
                      size="small"
                      active-text="已配置"
                      inactive-text="未配置"
                      style="--el-switch-on-color: #34c759"
                      @change="() => onResourceToggle(item)"
                    />
                  </div>
                </div>

                <!-- 链接 -->
                <a v-if="item.link" :href="item.link" target="_blank" class="detail-link" style="font-size: 0.75rem; color: #999; text-decoration: none">
                  查看原文 →
                </a>

                <!-- 负责人 -->
                <div v-if="item.owners && item.owners.length" style="margin-top: 6px; display: flex; gap: 4px; flex-wrap: wrap">
                  <el-tag v-for="owner in item.owners" :key="owner" size="small" type="info" effect="plain">{{ owner }}</el-tag>
                </div>

                <!-- 操作 -->
                <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid #f0f0f0; display: flex; align-items: center; justify-content: space-between">
                  <span style="font-size: 0.6875rem; color: #ccc">{{ item.source === 'news' ? '抓取' : '手动' }}</span>
                  <div class="flex gap-1">
                    <template v-if="item.source === 'news'">
                      <el-button size="small" text @click="emit('edit-annotation', item)">编辑备注</el-button>
                      <el-button size="small" text @click="emit('hide-news', item)">隐藏</el-button>
                    </template>
                    <template v-else>
                      <el-button size="small" text @click="emit('edit-event', item)">编辑</el-button>
                      <el-popconfirm title="确认删除？不可恢复" :icon="null" hide-icon width="180" placement="top" teleported @confirm="emit('delete-event', item)">
                        <template #reference>
                          <el-button size="small" text style="color: #ef4444">删除</el-button>
                        </template>
                      </el-popconfirm>
                    </template>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<style scoped>
/* 日期 pills 横向滚动 */
.date-pills {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  flex: 1;
  min-width: 0;
}
.date-pills::-webkit-scrollbar {
  display: none;
}

/* 日期 pill */
.date-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 12px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 150ms;
  min-width: 0;
}
.date-pill:active {
  background: #f5f5f5;
}
.date-pill.active {
  background: #111;
  border-color: #111;
}
.date-pill-label {
  font-size: 11px;
  color: #555;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.date-pill.active .date-pill-label {
  color: #fff;
}
.date-pill-count {
  font-size: 10px;
  color: #ccc;
  font-variant-numeric: tabular-nums;
}
.date-pill.active .date-pill-count {
  color: rgba(255, 255, 255, 0.6);
}
</style>
