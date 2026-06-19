<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo-section">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <h2>习题管理系统</h2>
      </div>

      <div class="nav-menu">
        <div class="nav-item" :class="{ active: $route.path === '/' }" @click="$router.push('/')">
          <el-icon><Document /></el-icon>
          <span>练习模式</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/plan' }" @click="$router.push('/plan')">
          <el-icon><List /></el-icon>
          <span>学习计划</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/import' }" @click="$router.push('/import')">
          <el-icon><Plus /></el-icon>
          <span>导入习题</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/wrong' }" @click="$router.push('/wrong')">
          <el-icon><CircleClose /></el-icon>
          <span>错题本</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/review' }" @click="$router.push('/review')">
          <el-icon><Refresh /></el-icon>
          <span>复习模式</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/important' }" @click="$router.push('/important')">
          <el-icon><Star /></el-icon>
          <span>重点题</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/trash' }" @click="$router.push('/trash')">
          <el-icon><Delete /></el-icon>
          <span>垃圾桶</span>
        </div>
        <div class="nav-item" :class="{ active: $route.path === '/settings' }" @click="$router.push('/settings')">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </div>
      </div>

      <div class="user-section">
        <div class="user-info">
          <div class="avatar">U</div>
          <div class="user-details">
            <span class="username">{{ username }}</span>
            <span class="logout-btn" @click="handleLogout">退出登录</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <div class="settings-page">
        <header class="page-header">
          <div>
            <h1>设置</h1>
            <p>配置 AI 讲解和数据管理。</p>
          </div>
        </header>

        <main class="settings-content">
          <section class="settings-card">
            <h2>DeepSeek API Key</h2>
            <p class="muted">
              后端会保存到项目根目录的 `.env` 文件。当前状态：{{ settings?.has_deepseek_api_key ? '已配置' : '未配置' }}
            </p>
            <div class="key-row">
              <el-input
                v-model="apiKey"
                type="password"
                show-password
                placeholder="sk-..."
                autocomplete="off"
              />
              <el-button type="primary" :icon="Check" :loading="saving" @click="saveKey">保存</el-button>
            </div>
          </section>

          <section class="settings-card">
            <h2>错题移除阈值</h2>
            <p class="muted">答对错题达到该次数后，才会从错题本移除（1-10）。</p>
            <div class="threshold-row">
              <el-input-number v-model="wrongThreshold" :min="1" :max="10" />
              <el-button type="primary" :icon="Check" :loading="savingThreshold" @click="saveThreshold">保存</el-button>
            </div>
          </section>

          <section class="settings-card danger">
            <h2>清空所有数据</h2>
            <p class="muted">会删除题目、练习记录和错题本，操作不可撤销。执行前必须输入当前登录密码。</p>
            <el-button type="danger" :icon="Delete" :loading="clearing" @click="clearData">清空所有数据</el-button>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { h, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElInput, ElMessage, ElMessageBox } from 'element-plus'
import { Check, CircleClose, Delete, Document, List, Plus, Refresh, Setting, Star } from '@element-plus/icons-vue'
import { clearAllData, getSettings, saveDeepSeekKey, saveWrongThreshold } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('auth_username') || '用户')
const settings = ref(null)
const apiKey = ref('')
const saving = ref(false)
const clearing = ref(false)
const wrongThreshold = ref(1)
const savingThreshold = ref(false)

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const loadSettings = async () => {
  try {
    settings.value = await getSettings()
    wrongThreshold.value = settings.value?.wrong_question_remove_threshold || 1
  } catch (error) {
    ElMessage.error(`加载设置失败：${error.response?.data?.detail || error.message}`)
  }
}

const saveThreshold = async () => {
  savingThreshold.value = true
  try {
    await saveWrongThreshold(wrongThreshold.value)
    ElMessage.success('错题移除阈值已保存')
    await loadSettings()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    savingThreshold.value = false
  }
}

const saveKey = async () => {
  if (!apiKey.value.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  saving.value = true
  try {
    await saveDeepSeekKey(apiKey.value.trim())
    ElMessage.success('API Key 已保存')
    apiKey.value = ''
    await loadSettings()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const promptPasswordConfirm = async () => {
  let password = ''

  await ElMessageBox({
    title: '密码确认',
    message: h('div', { class: 'danger-confirm' }, [
      h('p', { class: 'danger-confirm__text' }, '请输入当前登录密码后再清空所有数据。'),
      h(ElInput, {
        modelValue: password,
        'onUpdate:modelValue': (value) => {
          password = value
        },
        type: 'password',
        showPassword: true,
        placeholder: '请输入当前密码',
        autocomplete: 'current-password'
      })
    ]),
    showCancelButton: true,
    confirmButtonText: '确认清空',
    cancelButtonText: '取消',
    confirmButtonClass: 'el-button--danger',
    beforeClose: (action, instance, done) => {
      if (action !== 'confirm') {
        done()
        return
      }
      if (!password.trim()) {
        ElMessage.warning('请输入当前密码')
        return
      }
      done()
    }
  })

  return password.trim()
}

const clearData = async () => {
  try {
    const password = await promptPasswordConfirm()
    clearing.value = true
    await clearAllData(password)
    ElMessage.success('数据已清空')
    await loadSettings()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`清空失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    clearing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: white;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 100;
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-section .logo-icon {
  width: 40px;
  height: 40px;
  color: #3b82f6;
  margin-bottom: 12px;
}

.logo-section h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 4px;
  color: #94a3b8;
}

.nav-item:hover {
  background: rgba(59, 130, 246, 0.1);
  color: #e2e8f0;
}

.nav-item.active {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
}

.nav-item .el-icon {
  font-size: 20px;
}

.nav-item span {
  font-size: 14px;
  font-weight: 500;
}

.user-section {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
}

.user-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.username {
  font-weight: 500;
  font-size: 14px;
}

.logout-btn {
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
  transition: color 0.2s ease;
}

.logout-btn:hover {
  color: #ef4444;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f9ff 0%, #fafafa 100%);
}

.settings-page {
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.settings-content {
  max-width: 720px;
  margin: 24px auto;
  display: grid;
  gap: 16px;
}

.settings-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
}

.settings-card h2 {
  margin: 0 0 12px;
  font-size: 18px;
  color: #303133;
}

.settings-card.danger h2 {
  color: #f56c6c;
}

.muted {
  color: #909399;
  margin: 0 0 16px;
  font-size: 14px;
  line-height: 1.6;
}

.key-row,
.threshold-row {
  display: flex;
  gap: 12px;
}

.key-row .el-input {
  flex: 1;
}
</style>
