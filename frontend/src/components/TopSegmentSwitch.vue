<script setup>
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  modelValue: { type: String, required: true },
  options: { type: Array, default: () => [] },
})

const emit = defineEmits(['update:modelValue'])

const rootRef = ref(null)
const canDrag = ref(false)
const dragging = ref(false)
const dragTranslate = ref(0)
const suppressClick = ref(false)
let dragStartX = 0
let dragStartTranslate = 0
let segmentWidth = 0
let mediaQuery = null

const activeIndex = computed(() => {
  const index = props.options.findIndex(option => option.value === props.modelValue)
  return index >= 0 ? index : 0
})

const thumbStyle = computed(() => ({
  width: `calc((100% - 4px) / ${Math.max(props.options.length, 1)})`,
  transform: dragging.value ? `translateX(${dragTranslate.value}px)` : `translateX(${activeIndex.value * 100}%)`,
  transition: dragging.value ? 'none' : 'transform 180ms var(--ease-out-quart)',
}))

function selectOption(option) {
  if (suppressClick.value) return
  if (option.value !== props.modelValue) {
    emit('update:modelValue', option.value)
  }
}

function syncCanDrag() {
  canDrag.value = Boolean(mediaQuery?.matches)
}

function getSegmentMetrics() {
  const rect = rootRef.value?.getBoundingClientRect()
  if (!rect || !props.options.length) return false
  segmentWidth = (rect.width - 4) / props.options.length
  return segmentWidth > 0
}

// 安卓兼容：拖拽期间临时阻止浏览器接管水平手势
let horizontalConfirmed = false

function onDragTouchMove(e) {
  if (!dragging.value) return
  const dx = Math.abs(e.touches[0].clientX - dragStartX)
  // 首次移动超过 4px 且水平方向占主导时确认为拖拽
  if (!horizontalConfirmed && dx > 4) {
    horizontalConfirmed = true
  }
  if (horizontalConfirmed) {
    e.preventDefault()
  }
}

function addDragTouchListener(el) {
  horizontalConfirmed = false
  el.addEventListener('touchmove', onDragTouchMove, { passive: false })
}

function removeDragTouchListener(el) {
  el.removeEventListener('touchmove', onDragTouchMove)
}

function onPointerDown(event) {
  if (!canDrag.value || event.pointerType === 'mouse' || !getSegmentMetrics()) return
  dragging.value = true
  dragStartX = event.clientX
  dragStartTranslate = activeIndex.value * segmentWidth
  dragTranslate.value = dragStartTranslate
  event.currentTarget.setPointerCapture?.(event.pointerId)
  addDragTouchListener(event.currentTarget)
}

function onPointerMove(event) {
  if (!dragging.value) return
  const maxTranslate = segmentWidth * (props.options.length - 1)
  dragTranslate.value = Math.max(0, Math.min(maxTranslate, dragStartTranslate + event.clientX - dragStartX))
}

function onPointerUp(event) {
  if (!dragging.value) return
  dragging.value = false
  const moved = Math.abs(event.clientX - dragStartX)
  const targetIndex = Math.max(0, Math.min(props.options.length - 1, Math.round(dragTranslate.value / segmentWidth)))
  const target = props.options[targetIndex]
  if (target && target.value !== props.modelValue) {
    emit('update:modelValue', target.value)
  }
  if (moved > 4) {
    suppressClick.value = true
    window.setTimeout(() => {
      suppressClick.value = false
    }, 120)
  }
  event.currentTarget.releasePointerCapture?.(event.pointerId)
  removeDragTouchListener(event.currentTarget)
}

onMounted(() => {
  mediaQuery = window.matchMedia('(hover: none) and (pointer: coarse)')
  syncCanDrag()
  mediaQuery.addEventListener?.('change', syncCanDrag)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener?.('change', syncCanDrag)
})
</script>

<template>
  <div
    ref="rootRef"
    class="top-segment-switch"
    :class="{ 'is-draggable': canDrag, 'is-dragging': dragging }"
    :style="{ '--segment-count': options.length }"
    role="tablist"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  >
    <span class="top-segment-thumb" :style="thumbStyle"></span>
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="top-segment-item"
      :class="{ active: option.value === modelValue }"
      role="tab"
      :aria-selected="option.value === modelValue"
      @click="selectOption(option)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<style scoped>
.top-segment-switch {
  position: relative;
  display: grid;
  grid-template-columns: repeat(var(--segment-count), minmax(0, 1fr));
  width: min(100%, 280px);
  padding: 2px;
  border: 1px solid #e5e5e5;
  border-radius: 999px;
  background: #f5f5f5;
  overflow: hidden;
  user-select: none;
}

.top-segment-switch.is-draggable {
  touch-action: pan-y;
}

.top-segment-thumb {
  position: absolute;
  top: 2px;
  bottom: 2px;
  left: 2px;
  z-index: 0;
  border-radius: 999px;
  background: #111;
  pointer-events: none;
}

.top-segment-item {
  position: relative;
  z-index: 1;
  min-width: 0;
  height: 30px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: #777;
  font-size: 0.8125rem;
  font-weight: 600;
  cursor: pointer;
  transition: color 150ms var(--ease-out-quart), transform 150ms var(--ease-out-quart);
}

.top-segment-item.active {
  color: #fff;
}

.top-segment-item:active {
  transform: scale(0.96);
}

@media (hover: hover) and (pointer: fine) {
  .top-segment-item:not(.active):hover {
    color: #111;
  }
}

@media (max-width: 767px) {
  .top-segment-switch {
    width: 100%;
  }

  .top-segment-item {
    height: 28px;
    font-size: 0.75rem;
  }
}
</style>
