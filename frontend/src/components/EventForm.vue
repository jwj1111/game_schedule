<script setup>
import { ref, watch, computed } from 'vue'
import { message } from '../utils/message.js'

const ElMessage = message
const props = defineProps({
  visible: { type: Boolean, default: false },
  event: { type: Object, default: null },
  gameOptions: { type: Array, default: () => [] },
  defaultDate: { type: String, default: '' },
  saving: { type: Boolean, default: false },
  addingGame: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save', 'add-game'])

const isEdit = computed(() => !!props.event)

const form = ref({
  game: '',
  description: '',
  event_date: '',
  priority: null,
  resource_ready: false,
})

// 新建游戏相关状态（必须在 watch 之前声明）
const showNewGame = ref(false)
const newGameName = ref('')
const newGameOwnerTags = ref([])
const newOwnerInput = ref('')

watch([() => props.event, () => props.visible], () => {
  if (props.event) {
    form.value = {
      game: props.event.game,
      description: props.event.title || props.event.description || '',
      event_date: props.event.item_date || props.event.event_date || '',
      priority: props.event.priority || 0,
      resource_ready: props.event.resource_ready || false,
    }
  } else {
    form.value = {
      game: '',
      description: '',
      event_date: props.defaultDate || '',
      priority: null,
      resource_ready: false,
    }
  }
  showNewGame.value = false
  newGameName.value = ''
  newGameOwnerTags.value = []
  newOwnerInput.value = ''
}, { immediate: true })

function addOwnerTag() {
  const name = newOwnerInput.value.trim()
  if (name && !newGameOwnerTags.value.includes(name)) {
    newGameOwnerTags.value.push(name)
  }
  newOwnerInput.value = ''
}

function removeOwnerTag(tag) {
  newGameOwnerTags.value = newGameOwnerTags.value.filter(t => t !== tag)
}

function onAddGame() {
  const gameName = newGameName.value.trim()
  if (!gameName) return

  if (props.gameOptions.includes(gameName)) {
    ElMessage.warning(`游戏"${gameName}"已存在，请直接在下拉框选择`)
    return
  }

  emit('add-game', { game: gameName, owners: [...newGameOwnerTags.value] })
  form.value.game = gameName
  newGameName.value = ''
  newGameOwnerTags.value = []
  newOwnerInput.value = ''
  showNewGame.value = false
}

const isBusy = computed(() => props.saving || props.addingGame)

function onSave() {
  if (isBusy.value) return
  if (!form.value.game) return ElMessage.warning('请选择游戏')
  if (!form.value.description.trim()) return ElMessage.warning('请填写描述')
  if (!form.value.event_date) return ElMessage.warning('请选择日期')
  if (form.value.priority === null || form.value.priority === undefined) return ElMessage.warning('请设置优先级')
  emit('save', { ...form.value, alias: '', id: props.event?.id })
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑事件' : '新建事件'"
    width="90%"
    style="max-width: 440px"
    :close-on-click-modal="true"
    @close="emit('close')"
  >
    <el-form label-width="80px" size="default">
      <el-form-item label="游戏">
        <!-- 选择已有游戏 -->
        <div v-if="!showNewGame" class="flex gap-2 w-full">
          <el-select v-model="form.game" placeholder="选择游戏" filterable class="flex-1">
            <el-option v-for="g in gameOptions" :key="g" :label="g" :value="g" />
          </el-select>
          <el-button size="default" @click="showNewGame = true" title="添加新游戏">
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>

        <!-- 新建游戏模式 -->
        <div v-else class="flex flex-col gap-3 w-full">
          <div class="flex gap-2">
            <el-input v-model="newGameName" placeholder="输入新游戏名" class="flex-1" :disabled="isBusy" />
            <el-button size="default" @click="showNewGame = false" title="返回选择">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
          </div>

          <!-- 负责人 Tag 输入 -->
          <div>
            <div class="text-xs text-gray-400 mb-1.5">负责人（可选）</div>
            <div v-if="newGameOwnerTags.length" class="flex flex-wrap gap-1.5 mb-2">
              <el-tag
                v-for="tag in newGameOwnerTags"
                :key="tag"
                closable
                size="small"
                @close="removeOwnerTag(tag)"
              >
                {{ tag }}
              </el-tag>
            </div>
            <div class="flex gap-1.5">
              <el-input
                v-model="newOwnerInput"
                placeholder="输入姓名后回车"
                size="small"
                class="flex-1"
                :disabled="isBusy"
                @keyup.enter="addOwnerTag"
              />
              <el-button size="small" @click="addOwnerTag">添加</el-button>
            </div>
          </div>

          <el-button type="primary" size="default" :loading="addingGame" :disabled="isBusy" @click="onAddGame">确认添加游戏</el-button>
        </div>
      </el-form-item>

      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="2" placeholder="事件描述" :disabled="isBusy" />
      </el-form-item>
      <el-form-item label="日期">
        <el-date-picker
          v-model="form.event_date"
          type="date"
          placeholder="选择日期"
          value-format="YYYY-MM-DD"
          class="w-full"
        />
      </el-form-item>
      <el-form-item label="优先级">
        <div class="flex gap-1.5">
          <button
            v-for="opt in [
              { value: 3, label: '高', bg: 'bg-red-100', text: 'text-red-700', border: 'border-red-200' },
              { value: 2, label: '中', bg: 'bg-amber-100', text: 'text-amber-700', border: 'border-amber-200' },
              { value: 1, label: '低', bg: 'bg-blue-100', text: 'text-blue-700', border: 'border-blue-200' },
              { value: 0, label: '无', bg: 'bg-gray-100', text: 'text-gray-500', border: 'border-gray-300' },
            ]"
            :key="opt.value"
            type="button"
            class="px-3 py-1 text-xs rounded border pill-press cursor-pointer"
            :class="form.priority === opt.value ? [opt.bg, opt.text, opt.border] : ''"
            :style="form.priority !== opt.value ? { background: '#fff', borderColor: '#e5e5e5', color: '#ccc' } : {}"
            @click="form.priority = opt.value"
          >{{ opt.label }}</button>
        </div>
      </el-form-item>
      <el-form-item label="资源位">
        <el-switch v-model="form.resource_ready" active-text="已配置" inactive-text="未配置" style="--el-switch-on-color: #34c759" :disabled="isBusy" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button :disabled="isBusy" @click="emit('close')">取消</el-button>
      <el-button type="primary" :loading="saving" :disabled="isBusy" @click="onSave">{{ isEdit ? '保存' : '创建' }}</el-button>
    </template>
  </el-dialog>
</template>
