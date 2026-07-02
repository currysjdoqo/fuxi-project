import { computed, ref } from 'vue'
import { getCurrentUser } from '../api'
import { getAuthUserCode, getAuthUsername, updateAuthUserInfo } from '../utils/authStorage'

const userInfo = ref(null)
const loading = ref(false)

export const useUser = () => {
  const username = computed(() => {
    return userInfo.value?.username || getAuthUsername() || '用户'
  })

  const avatar = computed(() => {
    return userInfo.value?.avatar || null
  })

  const signature = computed(() => {
    return userInfo.value?.signature || ''
  })

  const userCode = computed(() => {
    return userInfo.value?.user_code || getAuthUserCode() || ''
  })

  const loadUserInfo = async () => {
    if (loading.value) return
    loading.value = true
    try {
      userInfo.value = await getCurrentUser()
      updateAuthUserInfo({
        username: userInfo.value?.username,
        userId: userInfo.value?.user_id,
        userCode: userInfo.value?.user_code,
      })
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
    userCode,
    loading,
    loadUserInfo,
    updateAvatar,
    updateSignature,
    resetUser,
  }
}
