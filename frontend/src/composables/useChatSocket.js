import { onBeforeUnmount, ref } from 'vue'
import { getAuthToken } from '../utils/authStorage'

function buildSocketUrl(token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  return `${protocol}//${window.location.host}/ws/chat?token=${encodeURIComponent(token)}`
}

export function useChatSocket(handlers = {}) {
  const socket = ref(null)
  const state = ref('idle')
  const isConnected = ref(false)
  const lastError = ref('')
  const activeFriendId = ref(null)

  let reconnectTimer = null
  let pingTimer = null
  let reconnectAttempt = 0
  let manuallyClosed = false

  const clearReconnectTimer = () => {
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  }

  const clearPingTimer = () => {
    if (pingTimer) {
      window.clearInterval(pingTimer)
      pingTimer = null
    }
  }

  const send = (payload) => {
    if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
      return false
    }
    socket.value.send(JSON.stringify(payload))
    return true
  }

  const connect = () => {
    const token = getAuthToken()
    if (!token) {
      state.value = 'offline'
      return
    }

    manuallyClosed = false
    clearReconnectTimer()
    state.value = reconnectAttempt > 0 ? 'reconnecting' : 'connecting'

    const ws = new WebSocket(buildSocketUrl(token))
    socket.value = ws

    ws.onopen = () => {
      reconnectAttempt = 0
      isConnected.value = true
      state.value = 'connected'
      lastError.value = ''
      clearPingTimer()
      pingTimer = window.setInterval(() => {
        send({ type: 'ping' })
      }, 25000)
      handlers.onOpen?.()
      if (activeFriendId.value) {
        send({ type: 'chat.open', friend_id: activeFriendId.value })
      }
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        handlers.onEvent?.(payload)
      } catch (error) {
        lastError.value = error.message || '消息解析失败'
      }
    }

    ws.onerror = () => {
      lastError.value = '实时连接异常'
      handlers.onError?.(lastError.value)
    }

    ws.onclose = () => {
      isConnected.value = false
      socket.value = null
      clearPingTimer()
      handlers.onClose?.()
      if (manuallyClosed) {
        state.value = 'offline'
        return
      }

      state.value = 'reconnecting'
      reconnectAttempt += 1
      const delay = Math.min(1000 * 2 ** Math.min(reconnectAttempt, 4), 10000)
      reconnectTimer = window.setTimeout(() => {
        connect()
      }, delay)
    }
  }

  const disconnect = () => {
    manuallyClosed = true
    clearReconnectTimer()
    clearPingTimer()
    if (socket.value && socket.value.readyState === WebSocket.OPEN) {
      socket.value.close(1000)
    }
    socket.value = null
    isConnected.value = false
    state.value = 'offline'
  }

  const openChat = (friendId) => {
    activeFriendId.value = friendId
    return send({ type: 'chat.open', friend_id: friendId })
  }

  const closeChat = () => {
    activeFriendId.value = null
    return send({ type: 'chat.close' })
  }

  const sendMessage = (receiverId, content) => {
    return send({ type: 'message.send', receiver_id: receiverId, content })
  }

  const ping = () => send({ type: 'ping' })

  onBeforeUnmount(() => {
    disconnect()
  })

  return {
    state,
    isConnected,
    lastError,
    connect,
    disconnect,
    openChat,
    closeChat,
    sendMessage,
    ping,
  }
}
