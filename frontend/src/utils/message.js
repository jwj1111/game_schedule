import { ElMessage } from 'element-plus'

const MESSAGE_COOLDOWN = 1200

let activeMessageInstance = null
let lastMessageKey = ''
let lastMessageAt = 0

function showMessage(type, text) {
  const content = String(text || '')
  const messageKey = `${type}::${content}`
  const now = Date.now()

  if (messageKey === lastMessageKey && now - lastMessageAt < MESSAGE_COOLDOWN) {
    return activeMessageInstance
  }

  lastMessageKey = messageKey
  lastMessageAt = now

  if (activeMessageInstance?.close) {
    activeMessageInstance.close()
    activeMessageInstance = null
  }

  let instance = null
  instance = ElMessage({
    type,
    message: content,
    customClass: 'schedule-message',
    offset: 24,
    duration: type === 'error' ? 2800 : 2200,
    showClose: false,
    grouping: false,
    onClose: () => {
      if (activeMessageInstance === instance) {
        activeMessageInstance = null
      }
    },
  })

  activeMessageInstance = instance
  return instance
}

export const message = {
  info(text) {
    return showMessage('info', text)
  },
  success(text) {
    return showMessage('success', text)
  },
  warning(text) {
    return showMessage('warning', text)
  },
  error(text) {
    return showMessage('error', text)
  },
}

