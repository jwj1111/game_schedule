<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  days: { type: Array, required: true },
  dataByDate: { type: Object, default: () => ({}) },
  maxShow: { type: Number, default: 3 },
  selectedDate: { type: String, default: '' },
})


const emit = defineEmits(['select-date', 'add-event'])

const weekDays = ['日', '一', '二', '三', '四', '五', '六']
const today = dayjs().format('YYYY-MM-DD')

const priorityClass = {
  3: 'bg-red-100 text-red-700 border-red-200',
  2: 'bg-amber-100 text-amber-700 border-amber-200',
  1: 'bg-blue-100 text-blue-700 border-blue-200',
  0: 'bg-gray-50 text-gray-500 border-gray-200',
}

const priorityDot = {
  3: '#ef4444',
  2: '#f59e0b',
  1: '#3b82f6',
  0: '#d4d4d4',
}

// 预计算每个日期格子的字符串和样式信息，避免模板中重复 format 调用
const processedDays = computed(() => {
  return props.days.map(day => {
    const dateStr = day.date.format('YYYY-MM-DD')
    const isToday = dateStr === today
    const isSelected = dateStr === props.selectedDate
    const dayOfWeek = day.date.day()
    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6

    let defaultBg = isToday ? '#f0f0f0' : (day.isCurrentMonth ? (isWeekend ? '#fafafa' : '#fff') : '#f5f5f5')
    let hoverBg = isToday ? '#ebebeb' : '#f5f5f5'
    let dateColor = isToday ? '#fff' : (day.isCurrentMonth ? '#555' : '#ccc')
    let dateWeight = isToday ? '600' : '400'

    if (isSelected) {
      defaultBg = day.isCurrentMonth ? '#fafafa' : '#f5f5f5'
      hoverBg = day.isCurrentMonth ? '#f5f5f5' : '#f0f0f0'
      dateColor = '#111'
      dateWeight = '600'
    }


    return {
      ...day,
      dateStr,
      dateNum: day.date.date(),
      isToday,
      isSelected,
      defaultBg,
      hoverBg,
      dateColor,
      dateWeight,
    }
  })
})


const gameTagsByDate = computed(() => {
  const result = {}
  for (const [dateStr, items] of Object.entries(props.dataByDate)) {
    const visible = items.filter(i => !i.hidden)
    const gameMap = {}
    for (const item of visible) {
      if (!gameMap[item.game]) {
        gameMap[item.game] = { game: item.game, maxPriority: 0, count: 0, allConfigured: true }
      }
      const g = gameMap[item.game]
      g.count++
      if (item.priority > g.maxPriority) g.maxPriority = item.priority
      if (!item.resource_ready) g.allConfigured = false
    }
    result[dateStr] = Object.values(gameMap).sort((a, b) => b.maxPriority - a.maxPriority)
  }
  return result
})

function getGameTags(dateStr) {
  return gameTagsByDate.value[dateStr] || []
}

function getPriorityClass(p) {
  return priorityClass[p] || priorityClass[0]
}
</script>

<template>
  <div class="w-full">
    <!-- 星期头 -->
    <div class="grid grid-cols-7" style="border-bottom: 1px solid #e5e5e5">
      <div
        v-for="(wd, wi) in weekDays"
        :key="wd"
        class="py-2.5 text-center"
        :style="{
          fontSize: '0.75rem',
          color: (wi === 0 || wi === 6) ? '#bbb' : '#999',
          fontWeight: '500',
          letterSpacing: '0.04em',
          backgroundColor: (wi === 0 || wi === 6) ? '#f7f7f7' : 'transparent',
        }"
      >
        {{ wd }}
      </div>
    </div>

    <!-- 日期网格 -->
    <div class="grid grid-cols-7" style="border-left: 1px solid #e5e5e5" role="grid" aria-label="日历">
      <div
        v-for="(day, idx) in processedDays"
        :key="idx"
        class="group cursor-pointer h-14 md:h-[140px]"
        :class="{ 'selected-cell': day.isSelected }"
        style="border-right: 1px solid #e5e5e5; border-bottom: 1px solid #e5e5e5; padding: 6px 6px 8px; transition: background-color 150ms; overflow: hidden"
        :style="{ backgroundColor: day.defaultBg }"
        @mouseenter="$event.currentTarget.style.backgroundColor = day.hoverBg"
        @mouseleave="$event.currentTarget.style.backgroundColor = day.defaultBg"
        role="gridcell"
        :tabindex="day.isCurrentMonth ? 0 : -1"
        @click="emit('select-date', day.dateStr)"
        @keyup.enter="emit('select-date', day.dateStr)"
      >

        <!-- 日期数字 + 添加按钮 -->
        <div class="flex items-center justify-between mb-1 md:mb-1.5">
          <span
            class="text-xs md:text-sm"
            :class="[day.isToday ? 'today-badge' : '', day.isSelected ? 'selected-date-number' : '']"
            :style="{
              color: day.dateColor,
              fontWeight: day.dateWeight,
              fontVariantNumeric: 'tabular-nums',
            }"
          >

            {{ day.dateNum }}
          </span>
          <button
            class="opacity-0 group-hover:opacity-100 transition-opacity hidden md:inline-block"
            style="font-size: 0.8125rem; color: #ccc; background: none; border: none; cursor: pointer; padding: 2px 4px; line-height: 1"
            aria-label="添加事项"
            @click.stop="emit('add-event', day.dateStr)"
            @mouseenter="$event.target.style.color='#555'"
            @mouseleave="$event.target.style.color='#ccc'"
          >+</button>
        </div>

        <!-- PC：浅色背景标签 -->
        <div class="hidden md:flex flex-col gap-1">
          <div
            v-for="(tag, i) in getGameTags(day.dateStr).slice(0, maxShow)"
            :key="i"
            class="truncate border tag-hover"
            :class="getPriorityClass(tag.maxPriority)"
            style="font-size: 0.6875rem; line-height: 1.5; padding: 2px 6px; border-radius: 4px"
          >
            <span v-if="tag.allConfigured" style="color: #22c55e; margin-right: 2px; font-size: 0.625rem">✓</span>
            <span>{{ tag.game }}</span>
            <span v-if="tag.count > 1" style="opacity: 0.7; margin-left: 2px; font-variant-numeric: tabular-nums">{{ tag.count }}</span>
          </div>
          <div
            v-if="getGameTags(day.dateStr).length > maxShow"
            style="font-size: 0.6875rem; color: #999; padding-left: 6px"
          >
            +{{ getGameTags(day.dateStr).length - maxShow }} 更多
          </div>
        </div>

        <!-- 移动端：彩色圆点 -->
        <div class="flex md:hidden flex-wrap gap-1 mt-1">
          <span
            v-for="(tag, i) in getGameTags(day.dateStr).slice(0, 5)"
            :key="i"
            style="width: 6px; height: 6px; border-radius: 50%; display: inline-block"
            :style="{ backgroundColor: priorityDot[tag.maxPriority] || '#d4d4d4' }"
            :title="tag.game"
          ></span>
          <span
            v-if="getGameTags(day.dateStr).length > 5"
            style="font-size: 0.5625rem; color: #999"
          >+{{ getGameTags(day.dateStr).length - 5 }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.selected-cell {
  position: relative;
}

.selected-cell::after {
  content: '';
  position: absolute;
  inset: 4px;
  border: 1.5px dashed #d6d6d6;
  border-radius: 10px;
  pointer-events: none;
}

.selected-date-number {
  color: #111 !important;
}
</style>


