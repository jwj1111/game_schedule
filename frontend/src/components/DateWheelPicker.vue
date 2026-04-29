<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '选择日期' },
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(false)

// 年月日范围
const currentYear = new Date().getFullYear()
const years = Array.from({ length: 21 }, (_, i) => currentYear - 10 + i) // 前10年~后10年
const months = Array.from({ length: 12 }, (_, i) => i + 1)

const selectedYear = ref(currentYear)
const selectedMonth = ref(new Date().getMonth() + 1)
const selectedDay = ref(new Date().getDate())

// 当月天数
const daysInMonth = computed(() => {
  return new Date(selectedYear.value, selectedMonth.value, 0).getDate()
})
const days = computed(() => Array.from({ length: daysInMonth.value }, (_, i) => i + 1))

// 日超出当月天数时修正
watch(daysInMonth, (max) => {
  if (selectedDay.value > max) selectedDay.value = max
})

// 从 modelValue 初始化
watch(() => props.modelValue, (val) => {
  if (val) {
    const parts = val.split('-')
    if (parts.length === 3) {
      selectedYear.value = parseInt(parts[0])
      selectedMonth.value = parseInt(parts[1])
      selectedDay.value = parseInt(parts[2])
    }
  }
}, { immediate: true })

const displayValue = computed(() => {
  if (!props.modelValue) return ''
  return props.modelValue
})

function open() {
  if (props.modelValue) {
    const parts = props.modelValue.split('-')
    if (parts.length === 3) {
      selectedYear.value = parseInt(parts[0])
      selectedMonth.value = parseInt(parts[1])
      selectedDay.value = parseInt(parts[2])
    }
  }
  visible.value = true
  document.body.style.overflow = 'hidden'
  nextTick(() => {
    scrollToSelected('year', years.indexOf(selectedYear.value))
    scrollToSelected('month', selectedMonth.value - 1)
    scrollToSelected('day', selectedDay.value - 1)
  })
}

function closePanel() {
  visible.value = false
  document.body.style.overflow = ''
}

onUnmounted(() => {
  if (visible.value) document.body.style.overflow = ''
})

function confirm() {
  const y = selectedYear.value
  const m = String(selectedMonth.value).padStart(2, '0')
  const d = String(selectedDay.value).padStart(2, '0')
  emit('update:modelValue', `${y}-${m}-${d}`)
  closePanel()
}

function cancel() {
  closePanel()
}

function clear() {
  emit('update:modelValue', '')
  closePanel()
}

// 滚轮逻辑
const ITEM_HEIGHT = 36

function scrollToSelected(type, idx) {
  const el = document.querySelector(`.wheel-${type}`)
  if (el) {
    el.scrollTop = idx * ITEM_HEIGHT
  }
}

function onScroll(type, items, setter) {
  const el = document.querySelector(`.wheel-${type}`)
  if (!el) return
  const idx = Math.round(el.scrollTop / ITEM_HEIGHT)
  const clamped = Math.max(0, Math.min(idx, items.length - 1))
  setter(items[clamped])
}

let scrollTimers = {}
function onWheelScroll(type, items, setter) {
  clearTimeout(scrollTimers[type])
  scrollTimers[type] = setTimeout(() => {
    onScroll(type, items, setter)
    // 对齐吸附
    const el = document.querySelector(`.wheel-${type}`)
    if (el) {
      const idx = Math.round(el.scrollTop / ITEM_HEIGHT)
      el.scrollTo({ top: idx * ITEM_HEIGHT, behavior: 'smooth' })
    }
  }, 80)
}

const pad = (n) => String(n).padStart(2, '0')
</script>

<template>
  <div class="inline-flex items-center">
    <!-- 触发按钮 -->
    <button
      class="wheel-trigger"
      @click="open"
    >
      <span :style="{ color: displayValue ? '#555' : '#ccc' }">
        {{ displayValue || placeholder }}
      </span>
      <svg v-if="displayValue" width="12" height="12" viewBox="0 0 12 12" @click.stop="clear" style="cursor: pointer; margin-left: 4px; opacity: 0.4">
        <circle cx="6" cy="6" r="5.5" fill="none" stroke="currentColor" stroke-width="1"/>
        <path d="M4 4L8 8M8 4L4 8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/>
      </svg>
    </button>

    <!-- 遮罩 + 面板 -->
    <Teleport to="body">
      <Transition name="wheel-fade">
        <div v-if="visible" class="wheel-overlay" @click.self="cancel">
          <div class="wheel-panel">
            <!-- 顶部操作栏 -->
            <div class="wheel-header">
              <button class="wheel-btn" @click="cancel">取消</button>
              <button class="wheel-btn" style="color: #999" @click="clear">清除</button>
              <button class="wheel-btn wheel-btn-confirm" @click="confirm">确定</button>
            </div>

            <!-- 三栏滚轮 -->
            <div class="wheel-body">
              <!-- 选中行高亮 -->
              <div class="wheel-highlight"></div>

              <!-- 年 -->
              <div class="wheel-column wheel-year" @scroll="onWheelScroll('year', years, v => selectedYear = v)">
                <div class="wheel-padding"></div>
                <div
                  v-for="y in years" :key="y"
                  class="wheel-item"
                  :class="{ active: y === selectedYear }"
                >{{ y }}年</div>
                <div class="wheel-padding"></div>
              </div>

              <!-- 月 -->
              <div class="wheel-column wheel-month" @scroll="onWheelScroll('month', months, v => selectedMonth = v)">
                <div class="wheel-padding"></div>
                <div
                  v-for="m in months" :key="m"
                  class="wheel-item"
                  :class="{ active: m === selectedMonth }"
                >{{ pad(m) }}月</div>
                <div class="wheel-padding"></div>
              </div>

              <!-- 日 -->
              <div class="wheel-column wheel-day" @scroll="onWheelScroll('day', days, v => selectedDay = v)">
                <div class="wheel-padding"></div>
                <div
                  v-for="d in days" :key="d"
                  class="wheel-item"
                  :class="{ active: d === selectedDay }"
                >{{ pad(d) }}日</div>
                <div class="wheel-padding"></div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.wheel-trigger {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 8px;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
  background: #fff;
  font-size: 12px;
  color: #555;
  font-family: inherit;
  cursor: pointer;
  outline: none;
  transition: border-color 150ms;
  min-width: 0;
  width: 100%;
}
.wheel-trigger:active {
  border-color: #ccc;
  background: #f5f5f5;
}

/* 遮罩 */
.wheel-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

/* 面板 */
.wheel-panel {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

/* 顶部栏 */
.wheel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
}
.wheel-btn {
  background: none;
  border: none;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  padding: 4px 8px;
  font-family: inherit;
}
.wheel-btn-confirm {
  color: #111;
  font-weight: 600;
}

/* 滚轮区域 */
.wheel-body {
  display: flex;
  height: 180px;
  position: relative;
  overflow: hidden;
}

/* 选中行高亮条 */
.wheel-highlight {
  position: absolute;
  top: 50%;
  left: 16px;
  right: 16px;
  height: 36px;
  transform: translateY(-50%);
  background: #f5f5f5;
  border-radius: 6px;
  pointer-events: none;
  z-index: 0;
}

/* 单列 */
.wheel-column {
  flex: 1;
  overflow-y: auto;
  scroll-snap-type: y mandatory;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior: contain;
  position: relative;
  z-index: 1;
}
.wheel-column::-webkit-scrollbar {
  display: none;
}

/* 上下留白（让第一项和最后一项能滚到中间） */
.wheel-padding {
  height: 72px; /* (180 - 36) / 2 */
}

/* 单项 */
.wheel-item {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #ccc;
  scroll-snap-align: center;
  transition: color 150ms;
  font-variant-numeric: tabular-nums;
  user-select: none;
}
.wheel-item.active {
  color: #111;
  font-weight: 500;
}

/* 进出动画 */
.wheel-fade-enter-active { transition: opacity 200ms ease; }
.wheel-fade-enter-active .wheel-panel { transition: transform 250ms cubic-bezier(0.25, 1, 0.5, 1); }
.wheel-fade-leave-active { transition: opacity 150ms ease; }
.wheel-fade-leave-active .wheel-panel { transition: transform 150ms ease; }
.wheel-fade-enter-from { opacity: 0; }
.wheel-fade-enter-from .wheel-panel { transform: translateY(100%); }
.wheel-fade-leave-to { opacity: 0; }
.wheel-fade-leave-to .wheel-panel { transform: translateY(100%); }
</style>
