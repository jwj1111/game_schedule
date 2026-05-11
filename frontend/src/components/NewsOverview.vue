<script setup>
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import OverviewItemGroups from './OverviewItemGroups.vue'

const props = defineProps({
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  canEdit: { type: Boolean, default: false },
  isItemActionPending: { type: Function, default: () => false },
})

const emit = defineEmits([
  'refresh',
  'edit-annotation', 'hide-news',
  'edit-event', 'delete-event',
  'quick-priority', 'quick-resource',
])

const activeSection = ref('latest')

const sectionOptions = [
  { label: '最新事项', value: 'latest' },
  { label: '临期事项', value: 'due' },
  { label: '过期事项', value: 'expired' },
]

const today = computed(() => dayjs().format('YYYY-MM-DD'))
const sevenDaysLater = computed(() => dayjs().add(6, 'day').format('YYYY-MM-DD'))
const fifteenDaysLater = computed(() => dayjs().add(14, 'day').format('YYYY-MM-DD'))
const expiredStartDate = computed(() => dayjs().subtract(7, 'day').format('YYYY-MM-DD'))

function isCreatedWithin24h(item) {
  const createdAt = dayjs(item.created_at)
  return createdAt.isValid() && dayjs().diff(createdAt, 'hour') < 24
}

function isKeyUnconfigured(item) {
  return item.priority > 0 && !item.resource_ready && !item.hidden
}

const latestItems = computed(() => props.items
  .filter(item => !item.hidden && isCreatedWithin24h(item))
  .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
)

const dueWithin7Items = computed(() => props.items
  .filter(item => isKeyUnconfigured(item) && item.item_date >= today.value && item.item_date <= sevenDaysLater.value)
  .sort((a, b) => a.item_date.localeCompare(b.item_date) || b.priority - a.priority)
)

const dueWithin15Items = computed(() => props.items
  .filter(item => isKeyUnconfigured(item) && item.item_date > sevenDaysLater.value && item.item_date <= fifteenDaysLater.value)
  .sort((a, b) => a.item_date.localeCompare(b.item_date) || b.priority - a.priority)
)

const expiredItems = computed(() => props.items
  .filter(item => isKeyUnconfigured(item) && item.item_date >= expiredStartDate.value && item.item_date < today.value)
  .sort((a, b) => b.item_date.localeCompare(a.item_date) || b.priority - a.priority)
)
</script>

<template>
  <section class="news-overview">
    <div class="overview-section-pills">
      <button
        v-for="option in sectionOptions"
        :key="option.value"
        type="button"
        class="overview-section-pill pill-press cursor-pointer"
        :style="activeSection === option.value
          ? { background: '#111', color: '#fff', borderColor: '#111' }
          : { background: '#fff', color: '#777', borderColor: '#e5e5e5' }"
        @click="activeSection = option.value"
      >
        {{ option.label }}
      </button>
    </div>

    <div class="overview-card" v-loading="props.loading">
      <div class="overview-card-head">
        <p v-if="activeSection === 'latest'" class="overview-desc">过去 24 小时入库的事项</p>
        <p v-else-if="activeSection === 'due'" class="overview-desc">15 天内未配置资源位的重点事项</p>
        <p v-else class="overview-desc">过去 7 天内仍未配置的重点事项</p>
        <el-button class="overview-refresh-button" size="small" :loading="props.loading" aria-label="刷新" @click="emit('refresh')">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M13 7.25A5 5 0 1 0 11.55 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M13 3.75V7.25H9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </el-button>
      </div>

      <div v-show="activeSection === 'latest'" class="overview-content">
        <OverviewItemGroups
          :items="latestItems"
          empty-text="今天暂无新入库事项"
          :can-edit="props.canEdit"
          :is-item-action-pending="isItemActionPending"
          @edit-annotation="emit('edit-annotation', $event)"
          @hide-news="emit('hide-news', $event)"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @quick-priority="emit('quick-priority', $event)"
          @quick-resource="emit('quick-resource', $event)"
        />
      </div>

      <div v-show="activeSection === 'due'" class="overview-content">
        <div class="overview-batch">
          <div class="overview-batch-title">7 天内 <span>{{ dueWithin7Items.length }} 条</span></div>
          <OverviewItemGroups
            :items="dueWithin7Items"
            empty-text="7 天内暂无临期事项"
            :can-edit="props.canEdit"
            :is-item-action-pending="isItemActionPending"
            @edit-annotation="emit('edit-annotation', $event)"
            @hide-news="emit('hide-news', $event)"
            @edit-event="emit('edit-event', $event)"
            @delete-event="emit('delete-event', $event)"
            @quick-priority="emit('quick-priority', $event)"
            @quick-resource="emit('quick-resource', $event)"
          />
        </div>
        <div class="overview-batch">
          <div class="overview-batch-title">15 天内 <span>{{ dueWithin15Items.length }} 条</span></div>
          <OverviewItemGroups
            :items="dueWithin15Items"
            empty-text="8-15 天内暂无临期事项"
            :can-edit="props.canEdit"
            :is-item-action-pending="isItemActionPending"
            @edit-annotation="emit('edit-annotation', $event)"
            @hide-news="emit('hide-news', $event)"
            @edit-event="emit('edit-event', $event)"
            @delete-event="emit('delete-event', $event)"
            @quick-priority="emit('quick-priority', $event)"
            @quick-resource="emit('quick-resource', $event)"
          />
        </div>
      </div>

      <div v-show="activeSection === 'expired'" class="overview-content">
        <OverviewItemGroups
          :items="expiredItems"
          empty-text="过去 7 天暂无过期未配置事项"
          :can-edit="props.canEdit"
          :is-item-action-pending="isItemActionPending"
          @edit-annotation="emit('edit-annotation', $event)"
          @hide-news="emit('hide-news', $event)"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @quick-priority="emit('quick-priority', $event)"
          @quick-resource="emit('quick-resource', $event)"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.news-overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.overview-section-pills {
  display: flex;
  align-items: center;
  gap: 6px;
}

.overview-section-pill {
  min-width: 88px;
  padding: 0.25rem 0.75rem;
  border: 1px solid;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 400;
  line-height: 1.5;
}

.overview-card {
  padding: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}

.overview-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.overview-desc {
  margin: 0;
  color: #888;
  font-size: 0.875rem;
  line-height: 1.5;
}

.overview-refresh-button {
  width: 1.5rem;
  height: 1.5rem;
  min-height: 1.5rem;
  padding: 0 !important;
  border: 0 !important;
  flex-shrink: 0;
  background: transparent !important;
  --el-button-text-color: #888 !important;
  --el-button-bg-color: transparent !important;
  --el-button-border-color: transparent !important;
  --el-button-hover-text-color: #555 !important;
  --el-button-hover-bg-color: #f5f5f5 !important;
  --el-button-hover-border-color: transparent !important;
  --el-button-active-bg-color: #ebebeb !important;
  --el-button-active-border-color: transparent !important;
}

.overview-content {
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid #f0f0f0;
}

.overview-batch {
  margin-bottom: 24px;
}

.overview-batch:last-child {
  margin-bottom: 0;
}

.overview-batch-title {
  margin-bottom: 10px;
  color: #111;
  font-size: 0.8125rem;
  font-weight: 600;
}

.overview-batch-title span {
  margin-left: 6px;
  color: #999;
  font-size: 0.6875rem;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 767px) {
  .overview-section-pills {
    gap: 4px;
  }

  .overview-section-pill {
    flex: 1;
    min-width: 0;
  }

  .overview-card {
    padding: 14px;
  }
}
</style>
