<script setup>
import { computed } from 'vue'

const props = defineProps({
  date: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  visible: { type: Boolean, default: false },
})

const emit = defineEmits([
  'close', 'edit-annotation', 'hide-news', 'restore-news',
  'edit-event', 'delete-event', 'add-event',
  'quick-priority', 'quick-resource',
])

const priorityOptions = [
  { value: 3, label: '高', bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200', activeBg: 'bg-red-500' },
  { value: 2, label: '中', bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200', activeBg: 'bg-amber-500' },
  { value: 1, label: '低', bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200', activeBg: 'bg-blue-500' },
  { value: 0, label: '无', bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-300', activeBg: 'bg-gray-400' },
]

const groupedGames = computed(() => {
  const visible = props.items.filter(i => !i.hidden)
  const map = {}
  for (const item of visible) {
    if (!map[item.game]) map[item.game] = []
    map[item.game].push(item)
  }
  const groups = Object.entries(map).map(([game, items]) => ({
    game,
    items: items.sort((a, b) => b.priority - a.priority),
    maxPriority: Math.max(...items.map(i => i.priority)),
  }))
  groups.sort((a, b) => b.maxPriority - a.maxPriority)
  return groups
})

const hiddenItems = computed(() => props.items.filter(i => i.hidden))

function onPriorityChange(item, newPriority) {
  emit('quick-priority', { item, priority: newPriority })
}
function onResourceToggle(item) {
  emit('quick-resource', { item, resource_ready: !item.resource_ready })
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    :title="`${date} 详情`"
    direction="rtl"
    size="90%"
    style="max-width: 440px"
    @close="emit('close')"
  >
    <div v-if="groupedGames.length > 0 || hiddenItems.length > 0" style="margin-bottom: 16px">
      <el-button size="small" @click="emit('add-event', date)">
        + 添加事项
      </el-button>
    </div>

    <div v-if="groupedGames.length === 0 && hiddenItems.length === 0" style="text-align: center; padding: 48px 0">
      <div style="color: #999; margin-bottom: 4px; font-size: 0.8125rem">当天没有排期</div>
      <div style="color: #ccc; margin-bottom: 16px; font-size: 0.75rem">清闲的一天，或者安排点什么？</div>
      <el-button size="small" @click="emit('add-event', date)">+ 添加事项</el-button>
    </div>

    <!-- 按游戏分组 -->
    <div v-for="group in groupedGames" :key="group.game" style="margin-bottom: 24px">
      <div style="font-size: 0.875rem; font-weight: 600; color: #111; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; line-height: 1.3">
        {{ group.game }}
        <span style="font-size: 0.6875rem; color: #999; font-weight: 400; font-variant-numeric: tabular-nums">({{ group.items.length }})</span>
      </div>

      <div style="display: flex; flex-direction: column; gap: 10px; padding-left: 10px; border-left: 2px solid #e5e5e5">
        <div
          v-for="item in group.items"
          :key="`${item.source}-${item.id}`"
          style="padding: 10px 14px; border-radius: 6px"
          :style="{ backgroundColor: '#fafafa' }"
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
                <el-popconfirm title="确认隐藏？可随时恢复" @confirm="emit('hide-news', item)">
                  <template #reference>
                    <el-button size="small" text>隐藏</el-button>
                  </template>
                </el-popconfirm>
              </template>
              <template v-else>
                <el-button size="small" text @click="emit('edit-event', item)">编辑</el-button>
                <el-popconfirm title="删除后无法恢复，确认删除？" @confirm="emit('delete-event', item)">
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

    <!-- 已隐藏 -->
    <div v-if="hiddenItems.length" style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #e5e5e5">
      <div style="font-size: 0.6875rem; color: #ccc; margin-bottom: 10px">已隐藏 ({{ hiddenItems.length }})</div>
      <div style="display: flex; flex-direction: column; gap: 6px">
        <div
          v-for="item in hiddenItems"
          :key="`hidden-${item.id}`"
          style="padding: 10px 14px; border: 1px dashed #e5e5e5; border-radius: 6px; opacity: 0.5; display: flex; align-items: center; justify-content: space-between"
        >
          <div style="flex: 1; min-width: 0">
            <span style="font-size: 0.75rem; color: #999">{{ item.game }}</span>
            <p style="font-size: 0.75rem; color: #ccc; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">{{ item.title }}</p>
          </div>
          <el-button size="small" text @click="emit('restore-news', item)">恢复</el-button>
        </div>
      </div>
    </div>
  </el-drawer>
</template>
