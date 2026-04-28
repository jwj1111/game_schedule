<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  gameOptions: { type: Array, default: () => [] },
  ownerOptions: { type: Array, default: () => [] },
})

const emit = defineEmits(['filter-change'])

const selectedGames = ref([])
const selectedOwners = ref([])
const selectedPriorities = ref([])
const selectedSource = ref(null)
const selectedResource = ref(null)
const keyword = ref('')
const mobileExpanded = ref(false)

let debounceTimer = null

function emitChange() {
  emit('filter-change', {
    games: selectedGames.value.join(','),
    owners: selectedOwners.value.join(','),
    source: selectedSource.value,
    priority: selectedPriorities.value.length ? selectedPriorities.value : null,
    resource: selectedResource.value,
    keyword: keyword.value.trim(),
  })
}

function debouncedEmit() {
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(emitChange, 300)
}

function togglePriority(val) {
  const idx = selectedPriorities.value.indexOf(val)
  if (idx >= 0) selectedPriorities.value.splice(idx, 1)
  else selectedPriorities.value.push(val)
  emitChange()
}

function toggleSource(val) {
  selectedSource.value = selectedSource.value === val ? null : val
  emitChange()
}

function toggleResource(val) {
  selectedResource.value = selectedResource.value === val ? null : val
  emitChange()
}

const hasFilter = computed(() =>
  selectedGames.value.length || selectedOwners.value.length ||
  selectedPriorities.value.length || selectedSource.value !== null ||
  selectedResource.value !== null || keyword.value.trim()
)

function clearAll() {
  selectedGames.value = []
  selectedOwners.value = []
  selectedPriorities.value = []
  selectedSource.value = null
  selectedResource.value = null
  keyword.value = ''
  emitChange()
}

watch([selectedGames, selectedOwners], emitChange)
watch(keyword, debouncedEmit)

const priorityButtons = [
  { value: 3, label: '高', activeClass: 'bg-red-100 text-red-700 border-red-200' },
  { value: 2, label: '中', activeClass: 'bg-amber-100 text-amber-700 border-amber-200' },
  { value: 1, label: '低', activeClass: 'bg-blue-100 text-blue-700 border-blue-200' },
  { value: 0, label: '无', activeClass: 'bg-gray-100 text-gray-600 border-gray-300' },
]
</script>

<template>
  <div class="w-full">
    <!-- 移动端：折叠按钮 + 搜索 -->
    <div class="md:hidden flex items-center gap-2 mb-2">
      <button
        class="flex items-center gap-1 px-3 py-1.5 border rounded-md text-sm transition-colors"
        style="border-color: #e5e5e5; color: #555"
        :style="{ backgroundColor: mobileExpanded ? '#f5f5f5' : '#fff' }"
        @click="mobileExpanded = !mobileExpanded"
      >
        <el-icon><Setting /></el-icon>
        筛选
        <span v-if="hasFilter" style="color: #111; font-weight: 600">·</span>
      </button>
      <span v-if="hasFilter" style="font-size: 12px; color: #999; cursor: pointer" @click="clearAll">清除</span>
      <el-input v-model="keyword" placeholder="搜索关键词" clearable size="small" class="flex-1" aria-label="关键词搜索" />
    </div>

    <!-- 移动端展开面板 -->
    <div v-if="mobileExpanded" class="md:hidden flex flex-col gap-3 mb-3 p-3 border rounded-lg filter-panel-enter" style="border-color: #e5e5e5; background: #fafafa">
      <!-- 游戏 -->
      <div class="flex items-center gap-2">
        <span style="font-size: 11px; color: #999; white-space: nowrap; width: 42px">游戏</span>
        <el-select
          v-model="selectedGames"
          multiple collapse-tags collapse-tags-tooltip
          placeholder="全部游戏" clearable size="small"
          class="flex-1"
          aria-label="游戏筛选"
        >
          <el-option v-for="g in gameOptions" :key="g" :label="g" :value="g" />
        </el-select>
      </div>
      <!-- 负责人 -->
      <div class="flex items-center gap-2">
        <span style="font-size: 11px; color: #999; white-space: nowrap; width: 42px">负责人</span>
        <el-select
          v-model="selectedOwners"
          multiple collapse-tags collapse-tags-tooltip
          placeholder="全部负责人" clearable size="small"
          class="flex-1"
          aria-label="负责人筛选"
        >
          <el-option v-for="o in ownerOptions" :key="o" :label="o" :value="o" />
        </el-select>
      </div>
      <!-- 优先级 -->
      <div class="flex items-center gap-1.5">
        <span style="font-size: 11px; color: #999; white-space: nowrap; width: 42px">优先级</span>
        <button
          v-for="p in priorityButtons"
          :key="p.value"
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedPriorities.includes(p.value) ? p.activeClass : ''"
          :style="!selectedPriorities.includes(p.value) ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="togglePriority(p.value)"
        >{{ p.label }}</button>
      </div>
      <!-- 来源 + 资源位 -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="flex items-center gap-1.5">
          <span style="font-size: 11px; color: #999; white-space: nowrap">来源</span>
          <button
            class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
            :class="selectedSource === 'news' ? 'bg-amber-50 text-amber-700 border-amber-200' : ''"
            :style="selectedSource !== 'news' ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
            @click="toggleSource('news')"
          >抓取</button>
          <button
            class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
            :class="selectedSource === 'event' ? 'bg-green-50 text-green-700 border-green-200' : ''"
            :style="selectedSource !== 'event' ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
            @click="toggleSource('event')"
          >手动</button>
        </div>
        <div class="flex items-center gap-1.5">
          <span style="font-size: 11px; color: #999; white-space: nowrap">资源位</span>
          <button
            class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
            :class="selectedResource === true ? 'bg-green-50 text-green-700 border-green-200' : ''"
            :style="selectedResource !== true ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
            @click="toggleResource(true)"
          >已配置</button>
          <button
            class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
            :class="selectedResource === false ? 'bg-gray-100 text-gray-600 border-gray-300' : ''"
            :style="selectedResource !== false ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
            @click="toggleResource(false)"
          >未配置</button>
        </div>
      </div>
    </div>

    <!-- PC：始终显示 -->
    <div class="hidden md:flex flex-wrap items-center gap-3">
      <!-- 下拉筛选组 -->
      <div class="flex items-center gap-2">
        <div class="flex items-center gap-1.5">
          <span style="font-size: 11px; color: #999; white-space: nowrap">游戏</span>
          <el-select
            v-model="selectedGames"
            multiple collapse-tags collapse-tags-tooltip
            placeholder="全部游戏" clearable size="small"
            style="width: 180px"
            aria-label="游戏筛选"
          >
            <el-option v-for="g in gameOptions" :key="g" :label="g" :value="g" />
          </el-select>
        </div>
        <div class="flex items-center gap-1.5">
          <span style="font-size: 11px; color: #999; white-space: nowrap">负责人</span>
          <el-select
            v-model="selectedOwners"
            multiple collapse-tags collapse-tags-tooltip
            placeholder="全部负责人" clearable size="small"
            style="width: 160px"
            aria-label="负责人筛选"
          >
            <el-option v-for="o in ownerOptions" :key="o" :label="o" :value="o" />
          </el-select>
        </div>
      </div>

      <span class="w-px h-5" style="background: #e0e0e0"></span>

      <!-- 优先级 pill 按钮组 -->
      <div class="flex items-center gap-1.5">
        <span style="font-size: 11px; color: #999; margin-right: 2px; white-space: nowrap">优先级</span>
        <button
          v-for="p in priorityButtons"
          :key="p.value"
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedPriorities.includes(p.value) ? p.activeClass : ''"
          :style="!selectedPriorities.includes(p.value) ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="togglePriority(p.value)"
        >{{ p.label }}</button>
      </div>

      <span class="w-px h-5" style="background: #e0e0e0"></span>

      <!-- 类型 pill -->
      <div class="flex items-center gap-1.5">
        <span style="font-size: 11px; color: #999; margin-right: 2px; white-space: nowrap">来源</span>
        <button
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedSource === 'news' ? 'bg-amber-50 text-amber-700 border-amber-200' : ''"
          :style="selectedSource !== 'news' ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="toggleSource('news')"
        >抓取</button>
        <button
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedSource === 'event' ? 'bg-green-50 text-green-700 border-green-200' : ''"
          :style="selectedSource !== 'event' ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="toggleSource('event')"
        >手动</button>
      </div>

      <span class="w-px h-5" style="background: #e0e0e0"></span>

      <!-- 资源位 pill -->
      <div class="flex items-center gap-1.5">
        <span style="font-size: 11px; color: #999; margin-right: 2px; white-space: nowrap">资源位</span>
        <button
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedResource === true ? 'bg-green-50 text-green-700 border-green-200' : ''"
          :style="selectedResource !== true ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="toggleResource(true)"
        >已配置</button>
        <button
          class="px-2.5 py-1 border rounded-md text-xs pill-press cursor-pointer"
          :class="selectedResource === false ? 'bg-gray-100 text-gray-600 border-gray-300' : ''"
          :style="selectedResource !== false ? { borderColor: '#e5e5e5', color: '#999', background: '#fff' } : {}"
          @click="toggleResource(false)"
        >未配置</button>
      </div>

      <!-- 清除 -->
      <span v-if="hasFilter" class="w-px h-5" style="background: #e0e0e0"></span>
      <span
        v-if="hasFilter"
        class="text-xs cursor-pointer"
        style="color: #999"
        @click="clearAll"
        @mouseenter="$event.target.style.color='#111'"
        @mouseleave="$event.target.style.color='#999'"
      >清除</span>
    </div>

    <!-- PC 搜索框：独立一行 -->
    <div class="hidden md:flex mt-2">
      <el-input
        v-model="keyword"
        placeholder="搜索资讯关键词…"
        clearable size="small"
        class="w-full"
        aria-label="关键词搜索"
      />
    </div>
  </div>
</template>
