<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'login'])

const password = ref('')

watch(() => props.visible, (visible) => {
  if (visible) password.value = ''
})

function close() {
  if (props.loading) return
  emit('update:visible', false)
}

function submit() {
  const value = password.value.trim()
  if (!value || props.loading) return
  emit('login', value)
}

function onOpened() {
  requestAnimationFrame(() => {
    document.querySelector('.admin-login-dialog input[type="password"]')?.focus()
  })
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="管理员登录"
    width="320px"
    class="admin-login-dialog"
    append-to-body
    destroy-on-close
    :close-on-click-modal="!loading"
    :close-on-press-escape="!loading"
    @opened="onOpened"
    @close="close"
  >
    <div class="admin-login-body">
      <p class="admin-login-desc">输入内部管理员密码，并编辑日历。</p>
      <el-input
        v-model="password"
        type="password"
        placeholder="管理员密码"
        show-password
        autocomplete="current-password"
        :disabled="loading"
        @keyup.enter="submit"
      />
    </div>
    <template #footer>
      <el-button :disabled="loading" @click="close">取消</el-button>
      <el-button type="primary" :loading="loading" :disabled="!password.trim()" @click="submit">登录</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
:global(.admin-login-dialog) {
  width: min(320px, calc(100vw - 64px)) !important;
}

.admin-login-body {
  display: grid;
  gap: 12px;
}

.admin-login-desc {
  margin: 0;
  color: #888;
  font-size: 0.8125rem;
  line-height: 1.6;
}
</style>
