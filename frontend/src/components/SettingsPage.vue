<script setup>
import { computed, ref, watch } from 'vue'
import BottomSheetSelect from './BottomSheetSelect.vue'
import { fetchOwners, fetchGames, createOwner, updateOwner, fetchHidden, updateAnnotation } from '../api/index.js'
import { message } from '../utils/message.js'

const props = defineProps({
  active: { type: Boolean, default: false },
})

const emit = defineEmits(['restore-item'])

const ElMessage = message
const activeSection = ref('owners')
const sectionOptions = [
  { label: '游戏负责人', value: 'owners' },
  { label: '已隐藏事项', value: 'hidden' },
]

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

const ownerRows = ref([])
const loadingOwners = ref(false)
const ownersLoaded = ref(false)

async function loadOwners(force = false) {
  if (loadingOwners.value || (ownersLoaded.value && !force)) return
  loadingOwners.value = true
  try {
    const gamesRes = await fetchGames()
    const allGames = gamesRes.games || []
    const ownersData = await fetchOwners()
    const ownerMap = {}
    for (const o of ownersData) {
      ownerMap[o.game] = { owners: o.owners }
    }
    ownerRows.value = allGames.map(game => ({
      game,
      owners: [...(ownerMap[game]?.owners || [])],
      exists: !!ownerMap[game],
    }))
    ownersLoaded.value = true
  } catch (e) {
    console.error(e)
    ElMessage.error('负责人加载失败')
  } finally {
    loadingOwners.value = false
  }
}

const selectedOwnerGames = ref([])
const ownerGameOptions = computed(() => ownerRows.value.map(row => row.game))
const filteredOwnerRows = computed(() => {
  if (!selectedOwnerGames.value.length) return ownerRows.value
  return ownerRows.value.filter(row => selectedOwnerGames.value.includes(row.game))
})

const ownerNameOptions = computed(() => {
  const names = new Set()
  for (const row of ownerRows.value) {
    for (const owner of row.owners || []) {
      if (owner) names.add(owner)
    }
  }
  return [...names].sort((a, b) => a.localeCompare(b))
})

const editingGame = ref(null)
const editingTags = ref([])
const editingInput = ref('')
const currentEditSaving = computed(() => (editingGame.value ? isActionPending(`save-owner:${editingGame.value}`) : false))

function startEdit(row) {
  editingGame.value = row.game
  editingTags.value = [...row.owners]
  editingInput.value = ''
}

function cancelEdit() {
  editingGame.value = null
  editingTags.value = []
  editingInput.value = ''
}

function addEditTag() {
  const name = editingInput.value.trim()
  if (name && !editingTags.value.includes(name)) {
    editingTags.value.push(name)
  }
  editingInput.value = ''
}

function removeEditTag(tag) {
  editingTags.value = editingTags.value.filter(t => t !== tag)
}

function queryOwnerSuggestions(query, callback) {
  try {
    const keyword = query.trim().toLowerCase()
    const suggestions = ownerNameOptions.value
      .filter(name => !editingTags.value.includes(name))
      .filter(name => !keyword || name.toLowerCase().includes(keyword))
      .map(name => ({ value: name }))
    callback(suggestions)
  } catch (e) {
    console.error(e)
    callback([])
  }
}

function onOwnerSuggestionSelect(option) {
  const name = option.value?.trim()
  if (name && !editingTags.value.includes(name)) {
    editingTags.value.push(name)
  }
  editingInput.value = ''
}

async function saveEdit(row) {
  await runLockedAction(`save-owner:${row.game}`, async () => {
    try {
      if (row.exists) {
        await updateOwner(row.game, { owners: editingTags.value })
      } else {
        await createOwner({ game: row.game, owners: editingTags.value })
        row.exists = true
      }
      row.owners = [...editingTags.value]
      editingGame.value = null
      ElMessage.success('负责人已更新')
    } catch (e) {
      ElMessage.error('更新失败: ' + e.message)
    }
  })
}

const hiddenItems = ref([])
const loadingHidden = ref(false)
const hiddenLoaded = ref(false)

async function loadHidden(force = false) {
  if (loadingHidden.value || (hiddenLoaded.value && !force)) return
  loadingHidden.value = true
  try {
    const res = await fetchHidden()
    hiddenItems.value = res.items || []
    hiddenLoaded.value = true
  } catch (e) {
    console.error(e)
    ElMessage.error('隐藏事项加载失败')
  } finally {
    loadingHidden.value = false
  }
}

const selectedHiddenGames = ref([])
const hiddenGameOptions = computed(() => [...new Set(hiddenItems.value.map(item => item.game))].sort())
const hiddenByGame = computed(() => {
  const map = {}
  const sourceItems = selectedHiddenGames.value.length
    ? hiddenItems.value.filter(item => selectedHiddenGames.value.includes(item.game))
    : hiddenItems.value
  for (const item of sourceItems) {
    if (!map[item.game]) map[item.game] = []
    map[item.game].push(item)
  }
  return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]))
})

async function restoreItem(item) {
  await runLockedAction(`restore-hidden:${item.id}`, async () => {
    try {
      await updateAnnotation(item.id, { hidden: false })
      hiddenItems.value = hiddenItems.value.filter(i => i.id !== item.id)
      emit('restore-item', item)
      ElMessage.success('已恢复显示')
    } catch (e) {
      ElMessage.error('恢复失败: ' + e.message)
    }
  })
}

function loadCurrentSection(force = false) {
  if (activeSection.value === 'owners') loadOwners(force)
  else loadHidden(force)
}

watch(() => props.active, (active) => {
  if (active) loadCurrentSection()
}, { immediate: true })

watch(activeSection, () => {
  if (props.active) loadCurrentSection()
})
</script>

<template>
  <section class="settings-page">
    <div class="settings-section-pills">
      <button
        v-for="option in sectionOptions"
        :key="option.value"
        type="button"
        class="settings-section-pill pill-press cursor-pointer"
        :style="activeSection === option.value
          ? { background: '#111', color: '#fff', borderColor: '#111' }
          : { background: '#fff', color: '#777', borderColor: '#e5e5e5' }"
        @click="activeSection = option.value"
      >
        {{ option.label }}
      </button>
    </div>

    <div v-show="activeSection === 'owners'" class="settings-card" v-loading="loadingOwners">
      <div class="settings-card-head">
        <div>
          <p class="settings-card-desc">为每个游戏指定负责人</p>
        </div>
        <el-button class="settings-refresh-button" size="small" :loading="loadingOwners" aria-label="刷新" @click="loadOwners(true)">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M13 7.25A5 5 0 1 0 11.55 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M13 3.75V7.25H9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </el-button>
      </div>

      <div class="settings-filter-line">
        <div class="settings-pc-filter">
          <el-select
            v-model="selectedOwnerGames"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            size="small"
            placeholder="游戏"
            style="width: 160px"
            aria-label="游戏负责人筛选"
          >
            <el-option v-for="game in ownerGameOptions" :key="game" :label="game" :value="game" />
          </el-select>
        </div>
        <div class="settings-mobile-filter">
          <BottomSheetSelect
            v-model="selectedOwnerGames"
            :options="ownerGameOptions"
            placeholder="全部游戏"
            title="选择游戏"
            class="flex-1"
          />
        </div>
      </div>

      <div class="settings-list">
        <div v-for="row in filteredOwnerRows" :key="row.game" class="settings-list-row">
          <div class="settings-row-main">
            <div class="settings-row-title">{{ row.game }}</div>

            <template v-if="editingGame === row.game">
              <div class="settings-tags editing-tags">
                <el-tag
                  v-for="tag in editingTags"
                  :key="tag"
                  :closable="!currentEditSaving"
                  size="small"
                  @close="removeEditTag(tag)"
                >
                  {{ tag }}
                </el-tag>
              </div>
              <div class="settings-edit-line">
                <el-autocomplete
                  v-model="editingInput"
                  size="small"
                  placeholder="输入或选择负责人"
                  :fetch-suggestions="queryOwnerSuggestions"
                  :trigger-on-focus="true"
                  :disabled="currentEditSaving"
                  class="settings-owner-autocomplete"
                  @select="onOwnerSuggestionSelect"
                  @keyup.enter="addEditTag"
                />
                <el-button size="small" :disabled="currentEditSaving" @click="addEditTag">添加</el-button>
              </div>
              <div class="settings-actions">
                <el-button size="small" type="primary" :loading="currentEditSaving" :disabled="currentEditSaving" @click="saveEdit(row)">保存</el-button>
                <el-button size="small" :disabled="currentEditSaving" @click="cancelEdit">取消</el-button>
              </div>
            </template>

            <template v-else>
              <div class="settings-tags">
                <el-tag v-for="owner in row.owners" :key="owner" size="small" type="info" effect="plain">{{ owner }}</el-tag>
                <span v-if="!row.owners.length" class="settings-empty-inline">未设置</span>
              </div>
            </template>
          </div>

          <el-button v-if="editingGame !== row.game" size="small" text type="primary" @click="startEdit(row)">编辑</el-button>
        </div>
      </div>

      <div v-if="!filteredOwnerRows.length && !loadingOwners" class="settings-empty">暂无游戏数据</div>
    </div>

    <div v-show="activeSection === 'hidden'" class="settings-card" v-loading="loadingHidden">
      <div class="settings-card-head">
        <div>
          <p class="settings-card-desc">查看被隐藏的抓取事项</p>
        </div>
        <el-button class="settings-refresh-button" size="small" :loading="loadingHidden" aria-label="刷新" @click="loadHidden(true)">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M13 7.25A5 5 0 1 0 11.55 11" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            <path d="M13 3.75V7.25H9.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </el-button>
      </div>

      <div class="settings-filter-line">
        <div class="settings-pc-filter">
          <el-select
            v-model="selectedHiddenGames"
            multiple
            collapse-tags
            collapse-tags-tooltip
            filterable
            clearable
            size="small"
            placeholder="游戏"
            style="width: 160px"
            aria-label="隐藏事项筛选"
          >
            <el-option v-for="game in hiddenGameOptions" :key="game" :label="game" :value="game" />
          </el-select>
        </div>
        <div class="settings-mobile-filter">
          <BottomSheetSelect
            v-model="selectedHiddenGames"
            :options="hiddenGameOptions"
            placeholder="全部游戏"
            title="选择游戏"
            class="flex-1"
          />
        </div>
      </div>

      <div class="hidden-group-list">
        <div v-for="[game, items] in hiddenByGame" :key="game" class="hidden-group-card">
          <div class="hidden-group-title">
            <span>{{ game }}</span>
            <span>{{ items.length }} 条</span>
          </div>
          <div class="hidden-item-list">
            <div v-for="item in items" :key="item.id" class="hidden-item-row">
              <div class="hidden-item-main">
                <div class="hidden-item-title">{{ item.title }}</div>
                <div class="hidden-item-date">{{ item.item_date }}</div>
              </div>
              <el-button
                size="small"
                type="primary"
                text
                :loading="isActionPending(`restore-hidden:${item.id}`)"
                :disabled="isActionPending(`restore-hidden:${item.id}`)"
                @click="restoreItem(item)"
              >
                恢复显示
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!hiddenByGame.length && !loadingHidden" class="settings-empty">暂无已隐藏事项</div>
    </div>
  </section>
</template>

<style scoped>
.settings-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-section-pills {
  display: flex;
  align-items: center;
  gap: 6px;
}

.settings-section-pill {
  min-width: 96px;
  padding: 0.25rem 0.75rem;
  border: 1px solid;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 400;
  line-height: 1.5;
}

.settings-card-desc {
  margin: 0;
  color: #888;
  font-size: 0.875rem;
  line-height: 1.5;
}

.settings-card {
  padding: 16px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}

.settings-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.settings-card-head > div {
  min-width: 0;
  flex: 1;
}

.settings-refresh-button {
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

.settings-filter-line {
  padding: 14px 0;
  border-bottom: 1px solid #f0f0f0;
}

.settings-pc-filter {
  display: none;
}

.settings-mobile-filter {
  display: flex;
  align-items: center;
}

.settings-list {
  display: flex;
  flex-direction: column;
}

.settings-list-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 2px;
  border-bottom: 1px solid #f0f0f0;
}

.settings-list-row:last-child {
  border-bottom: 0;
}

.settings-row-main {
  min-width: 0;
  flex: 1;
}

.settings-row-title {
  margin-bottom: 6px;
  color: #333;
  font-size: 0.875rem;
  font-weight: 400;
  letter-spacing: -0.003em;
  line-height: 1.35;
}

.settings-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.editing-tags {
  margin-bottom: 8px;
}

.settings-edit-line {
  display: flex;
  gap: 6px;
  max-width: 360px;
  margin-bottom: 8px;
}

.settings-owner-autocomplete {
  flex: 1;
}

.settings-actions {
  display: flex;
  gap: 8px;
}

.settings-empty,
.settings-empty-inline {
  color: #aaa;
  font-size: 0.75rem;
  line-height: 1.5;
}

.settings-empty {
  padding: 32px 0 16px;
  text-align: center;
}

.hidden-group-list {
  display: grid;
  gap: 12px;
  margin-top: 14px;
}

.hidden-group-card {
  padding: 12px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fafafa;
}

.hidden-group-title {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  color: #333;
  font-size: 0.8125rem;
  font-weight: 400;
  letter-spacing: -0.002em;
  line-height: 1.35;
}

.hidden-group-title span:last-child {
  color: #999;
  font-weight: 400;
}

.hidden-item-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hidden-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fff;
}

.hidden-item-main {
  min-width: 0;
  flex: 1;
}

.hidden-item-title {
  overflow: hidden;
  color: #555;
  font-size: 0.8125rem;
  line-height: 1.45;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hidden-item-date {
  margin-top: 2px;
  color: #aaa;
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}

@media (min-width: 768px) {
  .settings-pc-filter {
    display: block;
  }

  .settings-mobile-filter {
    display: none;
  }
}

@media (max-width: 767px) {
  .settings-section-pills {
    gap: 4px;
  }

  .settings-section-pill {
    flex: 1;
    min-width: 0;
  }

  .settings-card {
    padding: 14px;
  }



  .hidden-item-row {
    align-items: stretch;
    flex-direction: column;
  }

  .settings-edit-line {
    max-width: none;
  }
}
</style>
