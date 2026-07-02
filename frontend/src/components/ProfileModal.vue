<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="visible" class="profile-modal-overlay" @click.self="close">
        <div class="profile-modal">
          <div class="modal-bookmark"></div>
          
          <div class="modal-header">
            <div class="header-ribbon">
              <div class="ribbon-left"></div>
              <span class="ribbon-text">我的学习档案</span>
              <div class="ribbon-right"></div>
            </div>
            <button class="close-btn" @click="close">
              <el-icon><CircleClose /></el-icon>
            </button>
          </div>

          <div class="modal-body">
            <div class="paper-texture">
              <div class="avatar-section">
                <div class="avatar-wrapper">
                  <div class="avatar-frame">
                    <div class="avatar-inner" :style="{ background: displayAvatar ? `url(${displayAvatar}) center/cover` : undefined }">
                      <template v-if="!displayAvatar">{{ username.charAt(0).toUpperCase() }}</template>
                    </div>
                  </div>
                  <div class="avatar-badge">
                    <input
                      type="file"
                      ref="avatarInput"
                      accept="image/jpeg,image/png,image/gif,image/webp"
                      class="avatar-upload-input"
                      @change="handleAvatarUpload"
                    />
                    <button class="upload-btn" :loading="uploadingAvatar" @click="triggerAvatarUpload">
                      <el-icon><Camera /></el-icon>
                    </button>
                  </div>
                </div>
                <div class="user-info-text">
                  <h3 class="username-display">{{ username }}</h3>
                  <div class="user-code-display">
                    <span class="code-label">用户ID：</span>
                    <span class="code-value">{{ userCode }}</span>
                    <el-button size="small" @click="copyUserCode" class="copy-btn">
                      <el-icon><CopyDocument /></el-icon>
                    </el-button>
                  </div>
                  <p v-if="globalSignature" class="signature-display">{{ globalSignature }}</p>
                  <p v-else class="signature-placeholder">还没有学习宣言，写一句激励自己吧！</p>
                </div>
              </div>

              <div class="form-section">
                <div class="form-card">
                  <div class="card-icon">
                    <el-icon><EditPen /></el-icon>
                  </div>
                  <div class="card-content">
                    <label class="card-label">学习宣言</label>
                    <el-input
                      v-model="signature"
                      type="textarea"
                      :rows="2"
                      placeholder="写下你的学习目标..."
                      maxlength="100"
                      show-word-limit
                      class="signature-input"
                    />
                    <div class="card-actions">
                      <el-button type="primary" size="small" :loading="savingSignature" @click="saveSignature" class="action-btn">
                        <el-icon><Check /></el-icon>
                        保存宣言
                      </el-button>
                    </div>
                  </div>
                </div>

                <div class="form-card">
                  <div class="card-icon password-icon">
                    <el-icon><Lock /></el-icon>
                  </div>
                  <div class="card-content">
                    <label class="card-label">更新密码</label>
                    <div class="password-fields">
                      <el-input v-model="oldPassword" type="password" show-password placeholder="旧密码" class="password-input" />
                      <el-input v-model="newPassword" type="password" show-password placeholder="新密码（至少6位）" class="password-input" />
                      <el-input v-model="confirmPassword" type="password" show-password placeholder="确认新密码" class="password-input" />
                    </div>
                    <div class="card-actions">
                      <el-button type="primary" size="small" :loading="changingPassword" @click="handleChangePassword" class="action-btn">
                        <el-icon><Refresh /></el-icon>
                        修改密码
                      </el-button>
                    </div>
                  </div>
                </div>

                <div class="form-card">
                  <div class="card-icon settings-icon">
                    <el-icon><Setting /></el-icon>
                  </div>
                  <div class="card-content">
                    <label class="card-label">系统设置</label>
                    <p class="settings-hint">调整 API Key、错题阈值等学习配置</p>
                    <div class="card-actions">
                      <el-button size="small" @click="goToSettings" class="settings-btn">
                        <el-icon><ArrowRight /></el-icon>
                        前往设置
                      </el-button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <div class="footer-stamp">
              <span class="stamp-text">努力学习</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElInput, ElMessage } from 'element-plus'
import { ArrowRight, Camera, Check, CircleClose, CopyDocument, EditPen, Lock, Refresh, Setting } from '@element-plus/icons-vue'
import { updateProfile, uploadAvatar as apiUploadAvatar, changePassword as apiChangePassword } from '../api'
import { useUser } from '../composables/useUser'
import { clearAuthSession } from '../utils/authStorage'

const props = defineProps({
  visible: Boolean,
  username: String
})

const emit = defineEmits(['close', 'update:visible'])

const router = useRouter()
const { avatar: globalAvatar, signature: globalSignature, userCode, updateAvatar, updateSignature, loadUserInfo } = useUser()

const avatarInput = ref(null)
const signature = ref('')

const uploadingAvatar = ref(false)
const savingSignature = ref(false)
const changingPassword = ref(false)

const oldPassword = ref('')
const newPassword = ref('')
const confirmPassword = ref('')

const displayAvatar = computed(() => {
  return globalAvatar.value || null
})

watch(() => props.visible, async (val) => {
  if (val) {
    await loadUserInfo()
    signature.value = ''
  }
})

const close = () => {
  emit('update:visible', false)
}

const copyUserCode = async () => {
  if (!userCode.value) return
  try {
    await navigator.clipboard.writeText(userCode.value)
    ElMessage.success('用户ID已复制')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const triggerAvatarUpload = () => {
  avatarInput.value?.click()
}

const handleAvatarUpload = async (event) => {
  const file = event.target.files?.[0]
  if (!file) return

  if (file.size > 2 * 1024 * 1024) {
    ElMessage.error('图片大小不能超过 2MB')
    return
  }

  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('只支持 JPG、PNG、GIF、WebP 格式的图片')
    return
  }

  uploadingAvatar.value = true
  try {
    const result = await apiUploadAvatar(file)
    updateAvatar(result.avatar)
    ElMessage.success('头像上传成功')
  } catch (error) {
    ElMessage.error(`上传失败：${error.response?.data?.detail || error.message}`)
  } finally {
    uploadingAvatar.value = false
    event.target.value = ''
  }
}

const saveSignature = async () => {
  savingSignature.value = true
  try {
    const result = await updateProfile(signature.value)
    updateSignature(result.signature)
    ElMessage.success('学习宣言已保存')
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    savingSignature.value = false
  }
}

const handleChangePassword = async () => {
  if (!oldPassword.value.trim()) {
    ElMessage.warning('请输入旧密码')
    return
  }
  if (!newPassword.value.trim()) {
    ElMessage.warning('请输入新密码')
    return
  }
  if (newPassword.value.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (oldPassword.value === newPassword.value) {
    ElMessage.warning('新密码不能与旧密码相同')
    return
  }

  changingPassword.value = true
  try {
    await apiChangePassword(oldPassword.value, newPassword.value)
    ElMessage.success('密码修改成功，请重新登录')
    clearAuthSession()
    router.push('/auth/login')
  } catch (error) {
    ElMessage.error(`修改失败：${error.response?.data?.detail || error.message}`)
  } finally {
    changingPassword.value = false
    oldPassword.value = ''
    newPassword.value = ''
    confirmPassword.value = ''
  }
}

const goToSettings = () => {
  close()
  router.push('/settings')
}
</script>

<style scoped>
.profile-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  background: rgba(248, 245, 240, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.profile-modal {
  width: 100%;
  max-width: 520px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 
    0 1px 3px rgba(0, 0, 0, 0.08),
    0 4px 12px rgba(0, 0, 0, 0.06),
    0 0 0 1px rgba(0, 0, 0, 0.04),
    4px 4px 0 #e8e0d5;
  overflow: hidden;
  position: relative;
  animation: modalIn 0.4s ease-out;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: translateY(30px) rotate(-1deg);
  }
  to {
    opacity: 1;
    transform: translateY(0) rotate(0);
  }
}

.modal-bookmark {
  position: absolute;
  top: 0;
  right: 24px;
  width: 48px;
  height: 64px;
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
  border-radius: 0 0 8px 8px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(238, 90, 90, 0.3);
}

.modal-bookmark::before {
  content: '';
  position: absolute;
  top: 8px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 3px;
  background: rgba(255, 255, 255, 0.4);
  border-radius: 2px;
}

.modal-header {
  position: relative;
  padding: 32px 24px 24px;
  background: linear-gradient(180deg, #fdfbf7 0%, #f8f5f0 100%);
  border-bottom: 2px solid #e8e0d5;
  text-align: center;
}

.header-ribbon {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.ribbon-left,
.ribbon-right {
  flex: 1;
  height: 24px;
  background: linear-gradient(135deg, #63b3ed 0%, #4299e1 100%);
  clip-path: polygon(0 50%, 100% 0, 100% 100%);
}

.ribbon-right {
  clip-path: polygon(0 0, 100% 50%, 0 100%);
}

.ribbon-text {
  background: linear-gradient(135deg, #63b3ed 0%, #4299e1 100%);
  color: white;
  font-size: 16px;
  font-weight: 600;
  padding: 6px 20px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(66, 153, 225, 0.3);
}

.close-btn {
  position: absolute;
  right: 16px;
  top: 16px;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.05);
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

.modal-body {
  padding: 0;
}

.paper-texture {
  padding: 24px;
  background-image: 
    linear-gradient(90deg, rgba(0, 0, 0, 0.03) 1px, transparent 1px),
    linear-gradient(rgba(0, 0, 0, 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px dashed #e5e7eb;
}

.avatar-wrapper {
  position: relative;
  margin-bottom: 16px;
}

.avatar-frame {
  width: 112px;
  height: 112px;
  padding: 6px;
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  border-radius: 50%;
  box-shadow: 
    inset 0 2px 4px rgba(0, 0, 0, 0.05),
    0 4px 12px rgba(0, 0, 0, 0.08);
}

.avatar-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(135deg, #63b3ed 0%, #4299e1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 44px;
  font-weight: 700;
  color: white;
  transition: transform 0.3s ease;
}

.avatar-inner:hover {
  transform: scale(1.03);
}

.avatar-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
}

.upload-btn {
  width: 34px;
  height: 34px;
  border: 2px solid white;
  border-radius: 50%;
  background: linear-gradient(135deg, #48bb78 0%, #38a169 100%);
  color: white;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px rgba(72, 187, 120, 0.4);
  transition: all 0.2s ease;
}

.upload-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 4px 14px rgba(72, 187, 120, 0.5);
}

.avatar-upload-input {
  display: none;
}

.user-info-text {
  text-align: center;
}

.username-display {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 600;
  color: #1f2937;
  letter-spacing: 0.5px;
}

.user-code-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 8px;
}

.code-label {
  font-size: 13px;
  color: #9ca3af;
}

.code-value {
  font-size: 14px;
  font-weight: 500;
  color: #4f46e5;
  font-family: 'Courier New', monospace;
  background: #eef2ff;
  padding: 2px 8px;
  border-radius: 4px;
}

.copy-btn {
  padding: 2px 6px;
}

.signature-display {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
  font-style: italic;
  line-height: 1.6;
}

.signature-placeholder {
  margin: 0;
  font-size: 14px;
  color: #9ca3af;
  font-style: italic;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-card {
  display: flex;
  gap: 14px;
  padding: 18px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.form-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transform: translateY(-1px);
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #2563eb;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.15);
}

.card-icon.password-icon {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  color: #dc2626;
  box-shadow: 0 2px 8px rgba(220, 38, 38, 0.15);
}

.card-icon.settings-icon {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
  box-shadow: 0 2px 8px rgba(217, 119, 6, 0.15);
}

.card-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-label {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
}

.signature-input {
  font-size: 14px;
  border-radius: 6px;
}

.password-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.password-input {
  font-size: 13px;
  border-radius: 6px;
}

.settings-hint {
  margin: 0;
  font-size: 13px;
  color: #9ca3af;
  line-height: 1.5;
}

.card-actions {
  margin-top: 4px;
}

.action-btn {
  border-radius: 6px;
  font-weight: 500;
}

.settings-btn {
  border-radius: 6px;
  color: #4299e1;
  border-color: #4299e1;
}

.settings-btn:hover {
  background: #eff6ff;
}

.modal-footer {
  padding: 16px 24px;
  background: linear-gradient(180deg, #f8f5f0 0%, #f5f1e8 100%);
  border-top: 1px solid #e8e0d5;
  display: flex;
  justify-content: flex-end;
}

.footer-stamp {
  width: 64px;
  height: 64px;
  border: 3px solid #d6d3d1;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(-15deg);
  opacity: 0.6;
}

.stamp-text {
  font-size: 10px;
  font-weight: 700;
  color: #d6d3d1;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

:deep(.el-input__wrapper) {
  box-shadow: none;
  border-radius: 6px;
}

:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px rgba(66, 153, 225, 0.2);
}

:deep(.el-button--primary) {
  background: linear-gradient(135deg, #63b3ed 0%, #4299e1 100%);
  border: none;
}

:deep(.el-button--primary:hover) {
  background: linear-gradient(135deg, #4299e1 0%, #3182ce 100%);
}
</style>
