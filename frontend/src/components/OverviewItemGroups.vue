<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  emptyText: { type: String, default: '暂无事项' },
  isItemActionPending: { type: Function, default: () => false },
})

const emit = defineEmits([
  'edit-annotation', 'hide-news',
  'edit-event', 'delete-event',
  'quick-priority', 'quick-resource',
])

const priorityOptions = [
  { value: 3, label: '高', bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
  { value: 2, label: '中', bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
  { value: 1, label: '低', bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
  { value: 0, label: '无', bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-300' },
]

const groupedGames = computed(() => {
  const map = {}
  for (const item of props.items) {
    if (item.hidden) continue
    if (!map[item.game]) map[item.game] = []
    map[item.game].push(item)
  }
  return Object.entries(map)
    .map(([game, items]) => ({
      game,
      items: [...items].sort((a, b) => b.priority - a.priority || a.item_date.localeCompare(b.item_date)),
      maxPriority: Math.max(...items.map(i => i.priority)),
    }))
    .sort((a, b) => b.maxPriority - a.maxPriority || a.game.localeCompare(b.game))
})

function onPriorityChange(item, priority) {
  emit('quick-priority', { item, priority })
}

function onResourceToggle(item) {
  emit('quick-resource', { item, resource_ready: !item.resource_ready })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}
</script>

<template>
  <div>
    <div v-if="!groupedGames.length" class="overview-empty">{{ emptyText }}</div>

    <div v-for="group in groupedGames" :key="group.game" class="overview-game-group">
      <div class="overview-game-title">
        {{ group.game }}
        <span>{{ group.items.length }}</span>
      </div>

      <div class="overview-item-list">
        <div v-for="item in group.items" :key="`${item.source}-${item.id}`" class="overview-item-card">
          <div class="overview-item-head">
            <p class="overview-item-title">{{ item.alias || item.title }}</p>
            <span class="overview-date-chip">{{ formatDate(item.item_date) }}</span>
          </div>
          <p v-if="item.alias && item.source === 'news'" class="overview-origin-title">原标题：{{ item.title }}</p>

          <div class="overview-actions-row">
            <div class="overview-control-group">
              <span class="overview-control-label">优先级</span>
              <div class="flex gap-0.5">
                <button
                  v-for="opt in priorityOptions"
                  :key="opt.value"
                  class="px-2 py-0.5 text-xs rounded border transition-colors cursor-pointer"
                  :class="item.priority === opt.value ? [opt.bg, opt.text, opt.border] : ''"
                  :style="item.priority !== opt.value ? { background: '#fff', borderColor: '#e5e5e5', color: '#ccc' } : {}"
                  :disabled="props.isItemActionPending('priority', item)"
                  @click="onPriorityChange(item, opt.value)"
                >{{ opt.label }}</button>
              </div>
            </div>
            <div class="overview-control-group">
              <span class="overview-control-label">资源位</span>
              <el-switch
                :model-value="item.resource_ready"
                size="small"
                active-text="已配置"
                inactive-text="未配置"
                style="--el-switch-on-color: #34c759"
                :disabled="props.isItemActionPending('resource', item)"
                @change="() => onResourceToggle(item)"
              />
            </div>
          </div>

          <a v-if="item.link" :href="item.link" target="_blank" class="detail-link overview-link">查看原文 →</a>

          <div v-if="item.owners && item.owners.length" class="overview-owners">
            <el-tag v-for="owner in item.owners" :key="owner" size="small" type="info" effect="plain">{{ owner }}</el-tag>
          </div>

          <div class="overview-item-footer">
            <span>{{ item.source === 'news' ? '抓取' : '手动' }}</span>
            <div class="flex gap-1">
              <template v-if="item.source === 'news'">
                <el-button size="small" text @click="emit('edit-annotation', item)">编辑备注</el-button>
                <el-button size="small" text :disabled="props.isItemActionPending('hide', item)" @click="emit('hide-news', item)">隐藏</el-button>
              </template>
              <template v-else>
                <el-button size="small" text @click="emit('edit-event', item)">编辑</el-button>
                <el-popconfirm title="确认删除？不可恢复" :icon="null" hide-icon width="180" placement="top" teleported @confirm="emit('delete-event', item)">
                  <template #reference>
                    <el-button size="small" text style="color: #ef4444" :disabled="props.isItemActionPending('delete', item)">删除</el-button>
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

<style scoped>
.overview-empty {
  padding: 28px 0;
  color: #ccc;
  font-size: 0.8125rem;
  text-align: center;
}

.overview-game-group {
  margin-bottom: 20px;
}

.overview-game-group:last-child {
  margin-bottom: 0;
}

.overview-game-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  color: #111;
  font-size: 0.8125rem;
  font-weight: 600;
  line-height: 1.3;
}

.overview-game-title span {
  color: #999;
  font-size: 0.6875rem;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}

.overview-item-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-left: 10px;
  border-left: 2px solid #e5e5e5;
}

.overview-item-card {
  padding: 10px 14px;
  border-radius: 6px;
  background: #fafafa;
}

.overview-item-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}

.overview-item-title {
  margin: 0 0 8px;
  color: #111;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.overview-date-chip {
  flex-shrink: 0;
  color: #999;
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.overview-origin-title {
  margin: 0 0 6px;
  color: #ccc;
  font-size: 0.6875rem;
  line-height: 1.4;
}

.overview-actions-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 8px;
}

.overview-control-group {
  display: flex;
  align-items: center;
  gap: 6px;
}

.overview-control-label {
  color: #999;
  font-size: 0.6875rem;
}

.overview-link {
  color: #999;
  font-size: 0.75rem;
  text-decoration: none;
}

.overview-owners {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.overview-item-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px solid #f0f0f0;
}

.overview-item-footer > span {
  color: #ccc;
  font-size: 0.6875rem;
}
</style>
