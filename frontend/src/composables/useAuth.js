import { ref } from 'vue'
import {
  clearAuthToken,
  fetchAuthStatus,
  loginAdmin,
  logoutAdmin,
  onAuthUnauthorized,
  setAuthToken,
} from '../api/index.js'
import { message } from '../utils/message.js'

const ElMessage = message

const isAdmin = ref(false)
const authType = ref(null)
const authLoading = ref(false)
const loginDialogVisible = ref(false)
let unauthorizedBound = false

function setLoggedOut() {
  isAdmin.value = false
  authType.value = null
  clearAuthToken()
}

function bindUnauthorizedHandler() {
  if (unauthorizedBound) return
  unauthorizedBound = true
  onAuthUnauthorized(() => {
    const wasAdmin = isAdmin.value
    setLoggedOut()
    if (wasAdmin) ElMessage.warning('管理员登录已失效，请重新登录')
  })
}

export function useAuth() {
  bindUnauthorizedHandler()

  async function refreshAuthStatus() {
    authLoading.value = true
    try {
      const res = await fetchAuthStatus()
      isAdmin.value = Boolean(res.is_admin)
      authType.value = res.auth_type || null
      if (!isAdmin.value) clearAuthToken()
    } catch (e) {
      setLoggedOut()
    } finally {
      authLoading.value = false
    }
  }

  async function login(password) {
    if (authLoading.value) return false
    authLoading.value = true
    try {
      const res = await loginAdmin(password)
      setAuthToken(res.token)
      isAdmin.value = Boolean(res.is_admin)
      authType.value = res.auth_type || 'password'
      loginDialogVisible.value = false
      ElMessage.success('已进入管理员模式')
      return true
    } finally {
      authLoading.value = false
    }
  }

  async function logout() {
    if (authLoading.value) return
    authLoading.value = true
    try {
      await logoutAdmin().catch(() => null)
    } finally {
      setLoggedOut()
      authLoading.value = false
      ElMessage.success('已退出管理员模式')
    }
  }

  function openLoginDialog() {
    loginDialogVisible.value = true
  }

  function requireAdminAction() {
    if (isAdmin.value) return true
    ElMessage.warning('需要管理员权限')
    openLoginDialog()
    return false
  }

  return {
    isAdmin,
    authType,
    authLoading,
    loginDialogVisible,
    refreshAuthStatus,
    login,
    logout,
    openLoginDialog,
    requireAdminAction,
  }
}
