<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  item: { type: Object, default: null },
})

const emit = defineEmits(['close', 'save'])

const form = ref({
  priority: 0,
  alias: '',
  resource_ready: false,
})

watch(() => props.item, (val) => {
  if (val) {
    form.value = {
      priority: val.priority || 0,
      alias: val.alias || '',
      resource_ready: val.resource_ready || false,
    }
  }
}, { immediate: true })

function onSave() {
  emit('save', { ...form.value })
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="编辑备注"
    width="90%"
    style="max-width: 440px"
    :close-on-click-modal="true"
    @close="emit('close')"
  >
    <el-form label-width="80px" size="default">
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
      <el-form-item label="事件备注">
        <el-input v-model="form.alias" placeholder="对该资讯的个人备注" clearable />
      </el-form-item>
      <el-form-item label="资源位">
        <el-switch v-model="form.resource_ready" active-text="已配置" inactive-text="未配置" style="--el-switch-on-color: #34c759" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('close')">取消</el-button>
      <el-button type="primary" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>
