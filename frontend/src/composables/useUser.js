import { ref, computed, watch } from 'vue'
import { getCurrentUser } from '../api'

const userInfo = ref(null)
const loading = ref(false)

export const useUser = () => {
  const username = computed(() => {
    return userInfo.value?.username || localStorage.getItem('auth_username') || '用户'
  })

  const avatar = computed(() => {
    return userInfo.value?.avatar || null
  })

  const signature = computed(() => {
    return userInfo.value?.signature || ''
  })

  const loadUserInfo = async () => {
    if (loading.value) return
    loading.value = true
    try {
      userInfo.value = await getCurrentUser()
      if (userInfo.value?.username) {
        localStorage.setItem('auth_username', userInfo.value.username)
      }
    } catch (error) {
      console.error('加载用户信息失败:', error)
    } finally {
      loading.value = false
    }
  }

  const updateAvatar = (newAvatar) => {
    if (userInfo.value) {
      userInfo.value.avatar = newAvatar
    }
  }

  const updateSignature = (newSignature) => {
    if (userInfo.value) {
      userInfo.value.signature = newSignature
    }
  }

  const resetUser = () => {
    userInfo.value = null
  }

  return {
    userInfo,
    username,
    avatar,
    signature,
    loading,
    loadUserInfo,
    updateAvatar,
    updateSignature,
    resetUser
  }
}