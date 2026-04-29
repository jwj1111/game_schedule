<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  title: { type: String, default: '选择' },
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(false)
const search = ref('')
const tempSelected = ref([])

const filteredOptions = computed(() => {
  if (!search.value.trim()) return props.options
  const kw = search.value.trim().toLowerCase()
  return props.options.filter(o => o.toLowerCase().includes(kw))
})

const displayText = computed(() => {
  if (!props.modelValue.length) return ''
  if (props.modelValue.length === 1) return props.modelValue[0]
  return `${props.modelValue[0]} 等${props.modelValue.length}项`
})

function open() {
  tempSelected.value = [...props.modelValue]
  search.value = ''
  visible.value = true
  document.body.style.overflow = 'hidden'
}

function closePanel() {
  visible.value = false
  document.body.style.overflow = ''
}

function confirm() {
  emit('update:modelValue', [...tempSelected.value])
  closePanel()
}

function cancel() {
  closePanel()
}

function clear() {
  emit('update:modelValue', [])
  closePanel()
}

function toggle(option) {
  const idx = tempSelected.value.indexOf(option)
  if (idx >= 0) {
    tempSelected.value.splice(idx, 1)
  } else {
    tempSelected.value.push(option)
  }
}

function isChecked(option) {
  return tempSelected.value.includes(option)
}
</script>

<template>
  <div class="inline-flex items-center w-full">
    <!-- 触发按钮 -->
    <button class="sheet-trigger" @click="open">
      <span :style="{ color: displayText ? '#555' : '#ccc' }">
        {{ displayText || placeholder }}
      </span>
      <svg width="10" height="10" viewBox="0 0 10 10" style="margin-left: auto; opacity: 0.3; flex-shrink: 0">
        <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" stroke-width="1.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <!-- 遮罩 + 面板 -->
    <Teleport to="body">
      <Transition name="sheet-fade">
        <div v-if="visible" class="sheet-overlay" @click.self="cancel">
          <div class="sheet-panel">
            <!-- 顶部操作栏 -->
            <div class="sheet-header">
              <button class="sheet-btn" @click="cancel">取消</button>
              <span class="sheet-title">{{ title }}</span>
              <button class="sheet-btn sheet-btn-confirm" @click="confirm">确定</button>
            </div>

            <!-- 搜索 -->
            <div class="sheet-search">
              <input
                v-model="search"
                type="text"
                placeholder="搜索..."
                class="sheet-search-input"
              />
            </div>

            <!-- 选项列表 -->
            <div class="sheet-list">
              <div
                v-for="opt in filteredOptions"
                :key="opt"
                class="sheet-item"
                :class="{ checked: isChecked(opt) }"
                @click="toggle(opt)"
              >
                <span class="sheet-checkbox">
                  <svg v-if="isChecked(opt)" width="14" height="14" viewBox="0 0 14 14">
                    <rect x="0.5" y="0.5" width="13" height="13" rx="3" fill="#111" stroke="#111"/>
                    <path d="M3.5 7L6 9.5L10.5 4.5" stroke="#fff" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <svg v-else width="14" height="14" viewBox="0 0 14 14">
                    <rect x="0.5" y="0.5" width="13" height="13" rx="3" fill="none" stroke="#ddd"/>
                  </svg>
                </span>
                <span class="sheet-item-label">{{ opt }}</span>
              </div>

              <div v-if="!filteredOptions.length" class="sheet-empty">无匹配项</div>
            </div>

            <!-- 底部清除 -->
            <div class="sheet-footer" v-if="tempSelected.length">
              <button class="sheet-btn" style="color: #999; font-size: 12px" @click="tempSelected = []">
                清除全部 ({{ tempSelected.length }})
              </button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<style scoped>
.sheet-trigger {
  display: inline-flex;
  align-items: center;
  width: 100%;
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
  gap: 4px;
  min-width: 0;
}
.sheet-trigger:active {
  border-color: #ccc;
  background: #f5f5f5;
}

/* 遮罩 */
.sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0,0,0,0.3);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}

/* 面板 */
.sheet-panel {
  width: 100%;
  max-width: 400px;
  max-height: 70vh;
  background: #fff;
  border-radius: 12px 12px 0 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

/* 顶部栏 */
.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.sheet-title {
  font-size: 14px;
  font-weight: 600;
  color: #111;
}
.sheet-btn {
  background: none;
  border: none;
  font-size: 14px;
  color: #555;
  cursor: pointer;
  padding: 4px 8px;
  font-family: inherit;
}
.sheet-btn-confirm {
  color: #111;
  font-weight: 600;
}

/* 搜索 */
.sheet-search {
  padding: 8px 16px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}
.sheet-search-input {
  width: 100%;
  height: 32px;
  padding: 0 10px;
  border: 1px solid #e5e5e5;
  border-radius: 6px;
  font-size: 13px;
  color: #555;
  background: #fafafa;
  outline: none;
  font-family: inherit;
}
.sheet-search-input:focus {
  border-color: #ccc;
  background: #fff;
}

/* 列表 */
.sheet-list {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 4px 0;
}

/* 选项行 */
.sheet-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background-color 100ms;
  user-select: none;
}
.sheet-item:active {
  background: #f5f5f5;
}
.sheet-item.checked {
  background: #fafafa;
}

.sheet-checkbox {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

.sheet-item-label {
  font-size: 14px;
  color: #333;
}
.sheet-item.checked .sheet-item-label {
  color: #111;
  font-weight: 500;
}

.sheet-empty {
  padding: 24px;
  text-align: center;
  color: #ccc;
  font-size: 13px;
}

/* 底部 */
.sheet-footer {
  padding: 8px 16px;
  border-top: 1px solid #f0f0f0;
  flex-shrink: 0;
}

/* 进出动画 */
.sheet-fade-enter-active { transition: opacity 200ms ease; }
.sheet-fade-enter-active .sheet-panel { transition: transform 250ms cubic-bezier(0.25, 1, 0.5, 1); }
.sheet-fade-leave-active { transition: opacity 150ms ease; }
.sheet-fade-leave-active .sheet-panel { transition: transform 150ms ease; }
.sheet-fade-enter-from { opacity: 0; }
.sheet-fade-enter-from .sheet-panel { transform: translateY(100%); }
.sheet-fade-leave-to { opacity: 0; }
.sheet-fade-leave-to .sheet-panel { transform: translateY(100%); }
</style>
