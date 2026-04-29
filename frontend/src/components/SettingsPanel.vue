<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  fetchOwners, fetchGames, createOwner, updateOwner,
  fetchHidden, updateAnnotation,
} from '../api/index.js'

const props = defineProps({
  visible: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'restore-item'])

const activeTab = ref('owners')

// ==================== 负责人管理 ====================
const ownerRows = ref([])
const loadingOwners = ref(false)

async function loadOwners() {
  loadingOwners.value = true
  try {
    const gamesRes = await fetchGames()
    const allGames = gamesRes.games || []
    const ownersData = await fetchOwners()
    const ownerMap = {}
    for (const o of ownersData) {
      ownerMap[o.game] = { id: o.id, owners: o.owners }
    }
    ownerRows.value = allGames.map(game => ({
      game,
      owners: [...(ownerMap[game]?.owners || [])],
      exists: !!ownerMap[game],
    }))
  } catch (e) {
    console.error(e)
  } finally {
    loadingOwners.value = false
  }
}

// 编辑状态
const editingGame = ref(null)
const editingTags = ref([])
const editingInput = ref('')

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

async function saveEdit(row) {
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
}

// ==================== 已隐藏数据 ====================
const hiddenItems = ref([])
const loadingHidden = ref(false)

async function loadHidden() {
  loadingHidden.value = true
  try {
    const res = await fetchHidden()
    hiddenItems.value = res.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loadingHidden.value = false
  }
}

async function restoreItem(item) {
  try {
    await updateAnnotation(item.id, { hidden: false })
    hiddenItems.value = hiddenItems.value.filter(i => i.id !== item.id)
    emit('restore-item', item)
    ElMessage.success('已恢复显示')
  } catch (e) {
    ElMessage.error('恢复失败: ' + e.message)
  }
}

// 按游戏分组
const hiddenByGame = computed(() => {
  const map = {}
  for (const item of hiddenItems.value) {
    if (!map[item.game]) map[item.game] = []
    map[item.game].push(item)
  }
  return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]))
})

function onTabChange(tab) {
  if (tab === 'owners') loadOwners()
  if (tab === 'hidden') loadHidden()
}

watch(() => props.visible, (val) => {
  if (val) {
    if (activeTab.value === 'owners') loadOwners()
    else loadHidden()
  }
})

// ==================== 移动端右滑关闭 ====================
let touchStartX = 0
let touchStartY = 0

function onTouchStart(e) {
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
}

function onTouchEnd(e) {
  const dx = e.changedTouches[0].clientX - touchStartX
  const dy = Math.abs(e.changedTouches[0].clientY - touchStartY)
  if (dx > 120 && dx > dy * 1.5) {
    emit('close')
  }
}
</script>

<template>
  <el-drawer
    :model-value="visible"
    title="设置"
    direction="rtl"
    size="90%"
    style="max-width: 500px"
    @close="emit('close')"
  >
    <div
      style="min-height: 100%"
      @touchstart.passive="onTouchStart"
      @touchend.passive="onTouchEnd"
    >
    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <!-- Tab 1：负责人管理 -->
      <el-tab-pane label="游戏负责人" name="owners">
        <div v-loading="loadingOwners">
          <p class="text-xs text-gray-400 mb-4">为每个游戏指定负责人</p>

          <div v-for="row in ownerRows" :key="row.game" class="flex items-start justify-between py-3.5 px-1" style="border-bottom: 1px solid #f0f0f0">
            <div class="flex-1">
              <div class="text-sm font-medium text-gray-700 mb-1.5">{{ row.game }}</div>

              <!-- 编辑模式 -->
              <template v-if="editingGame === row.game">
                <div class="flex flex-wrap gap-1.5 mb-2">
                  <el-tag
                    v-for="tag in editingTags"
                    :key="tag"
                    closable
                    size="small"
                    @close="removeEditTag(tag)"
                  >
                    {{ tag }}
                  </el-tag>
                </div>
                <div class="flex gap-1.5 mb-2">
                  <el-input
                    v-model="editingInput"
                    size="small"
                    placeholder="输入姓名后回车"
                    class="flex-1"
                    @keyup.enter="addEditTag"
                  />
                  <el-button size="small" @click="addEditTag">添加</el-button>
                </div>
                <div class="flex gap-2">
                  <el-button size="small" type="primary" @click="saveEdit(row)">保存</el-button>
                  <el-button size="small" @click="cancelEdit">取消</el-button>
                </div>
              </template>

              <!-- 展示模式 -->
              <template v-else>
                <div class="flex gap-1.5 flex-wrap">
                  <el-tag v-for="o in row.owners" :key="o" size="small" type="info" effect="plain">{{ o }}</el-tag>
                  <span v-if="!row.owners.length" class="text-xs text-gray-400">未设置</span>
                </div>
              </template>
            </div>
            <el-button v-if="editingGame !== row.game" size="small" text type="primary" @click="startEdit(row)">
              编辑
            </el-button>
          </div>

          <div v-if="!ownerRows.length" class="text-gray-400 text-center py-8">暂无游戏数据</div>
        </div>
      </el-tab-pane>

      <!-- Tab 2：已隐藏数据 -->
      <el-tab-pane label="已隐藏事项" name="hidden">
        <div v-loading="loadingHidden">
          <div v-for="[game, items] in hiddenByGame" :key="game" class="mb-4">
            <div class="text-sm font-semibold text-gray-700 mb-2">
              {{ game }}
              <span class="text-xs text-gray-400 font-normal">({{ items.length }})</span>
            </div>
            <div class="flex flex-col gap-1.5 pl-2 border-l border-gray-200">
              <div
                v-for="item in items"
                :key="item.id"
                class="flex items-center justify-between p-2 bg-gray-50 rounded"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-xs text-gray-600 truncate">{{ item.title }}</div>
                  <div class="text-[10px] text-gray-400">{{ item.item_date }}</div>
                </div>
                <el-button size="small" type="primary" text @click="restoreItem(item)">
                  恢复显示
                </el-button>
              </div>
            </div>
          </div>

          <div v-if="!hiddenItems.length" class="text-gray-400 text-center py-6">暂无已隐藏事项</div>
        </div>
      </el-tab-pane>
    </el-tabs>
    </div>
  </el-drawer>
</template>
