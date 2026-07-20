<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
    <nav class="sidebar">
      <div class="logo-section">
        <h2>涔犻绠＄悊绯荤粺</h2>
      </div>

      <div class="nav-menu">
        <div class="nav-item" :class="{ active: $route.path === '/' }" @click="$router.push('/')"><el-icon><Document /></el-icon><span>缁冧範妯″紡</span></div>
        <div class="nav-item" :class="{ active: $route.path === '/plan' }" @click="$router.push('/plan')"><el-icon><List /></el-icon><span>瀛︿範璁″垝</span></div>
        <div class="nav-item" :class="{ active: $route.path === '/import' }" @click="$router.push('/import')"><el-icon><Plus /></el-icon><span>瀵煎叆涔犻</span></div>
        <div class="nav-item" :class="{ active: $route.path === '/review' }" @click="$router.push('/review')"><el-icon><Refresh /></el-icon><span>澶嶄範妯″紡</span></div>
        <div class="nav-item" :class="{ active: $route.path === '/trash' }" @click="$router.push('/trash')"><el-icon><Delete /></el-icon><span>鍨冨溇妗?</span></div>
        <div class="nav-item" :class="{ active: $route.path === '/settings' }" @click="$router.push('/settings')"><el-icon><Setting /></el-icon><span>璁剧疆</span></div>
      </div>

      <div class="user-section">
        <div class="user-info">
          <div class="avatar" :style="{ background: avatar ? `url(${avatar}) center/cover` : undefined }" @click="showProfileModal = true">
            <template v-if="!avatar">{{ username.charAt(0).toUpperCase() }}</template>
          </div>
          <div class="user-details">
            <span class="username">{{ username }}</span>
            <span class="logout-btn" @click="handleLogout">閫€鍑虹櫥褰?</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <button v-if="!isMobileNav" type="button" class="desktop-sidebar-handle" :class="{ collapsed: sidebarCollapsed }" @click="toggleSidebar">
        {{ sidebarCollapsed ? '>' : '<' }}
      </button>

      <div class="settings-page">
        <header class="page-header">
          <el-button v-if="isMobileNav" circle text class="header-nav-btn" :icon="Menu" @click="toggleMobileNav" />
          <div>
            <h1>璁剧疆</h1>
            <p>DeepSeek 鍩虹銆佸ソ鍙栥€佷細鍛樺拰次卡</p>
          </div>
        </header>

        <main class="settings-content">
          <section class="settings-card hero-card">
            <div class="hero-head">
              <div>
                <p class="eyebrow">ACCOUNT</p>
                <h2>AI 鏉ユ簮涓庨搴?</h2>
              </div>
              <el-tag :type="settings?.ai_provider === 'custom' ? 'success' : 'info'">
                {{ settings?.ai_provider === 'custom' ? '个人 Key' : '平台 Key' }}
              </el-tag>
            </div>

            <div class="stats-grid">
              <div class="stat-box"><span>会员</span><strong>{{ settings?.member_expires_at ? '已开通' : '未开通' }}</strong></div>
              <div class="stat-box"><span>会员剩余</span><strong>{{ settings?.member_calls_remaining || 0 }} 次</strong></div>
              <div class="stat-box"><span>次卡余额</span><strong>{{ settings?.call_credits || 0 }} 次</strong></div>
              <div class="stat-box"><span>每日免费</span><strong>{{ settings?.free_calls_remaining_today || 0 }} 次</strong></div>
            </div>
          </section>

          <section class="settings-card">
            <div class="card-title-row">
              <h2>AI 配置</h2>
              <el-tag v-if="settings?.has_custom_ai_api_key" type="success" effect="plain">个人 Key 已保存</el-tag>
            </div>

            <div class="field-block">
              <label>AI 来源</label>
              <el-radio-group v-model="aiProvider" @change="handleProviderChange">
                <el-radio-button label="platform">平台 DeepSeek</el-radio-button>
                <el-radio-button label="custom">我的 DeepSeek Key</el-radio-button>
              </el-radio-group>
              <p class="hint">平台模式走会员/免费次数；个人模式使用你自己的 Key，不扣平台额度。</p>
            </div>

            <div class="field-block">
              <label>平台 DeepSeek API Key</label>
              <div class="inline-row">
                <el-input v-model="platformApiKey" type="password" show-password placeholder="平台统一配置" />
                <el-button type="primary" :loading="savingPlatformKey" @click="savePlatformKey">保存</el-button>
              </div>
            </div>

            <div class="field-block">
              <label>个人 DeepSeek API Key</label>
              <div class="inline-row">
                <el-input v-model="customApiKey" type="password" show-password placeholder="只对当前用户生效" />
                <el-button type="primary" :loading="savingCustomKey" @click="saveCustomKey">保存</el-button>
                <el-button :disabled="!settings?.has_custom_ai_api_key" :loading="deletingCustomKey" @click="deleteCustomKey">删除</el-button>
              </div>
            </div>

            <div class="key-foot">
              <span>平台 Key：{{ settings?.has_deepseek_api_key ? '已配置' : '未配置' }}</span>
              <span>个人 Key：{{ settings?.has_custom_ai_api_key ? '已配置' : '未配置' }}</span>
            </div>
          </section>

          <section class="settings-card">
            <div class="card-title-row">
              <h2>邀请码</h2>
              <el-tag type="warning" effect="plain">{{ settings?.invite_code || '未生成' }}</el-tag>
            </div>
            <div class="inline-row">
              <el-input :model-value="settings?.invite_code || ''" readonly />
              <el-button @click="copyInviteCode">复制</el-button>
            </div>
            <div class="info-list">
              <div>余额：{{ ((settings?.balance_cents || 0) / 100).toFixed(2) }} 元</div>
              <div>被邀请人：{{ settings?.invited_by_id || '无' }}</div>
            </div>
          </section>

          <section class="settings-card">
            <h2>错题阈值</h2>
            <p class="hint">答对达到该次数后，从错题本移除。</p>
            <div class="inline-row">
              <el-input-number v-model="wrongThreshold" :min="1" :max="10" />
              <el-button type="primary" :loading="savingThreshold" @click="saveThreshold">保存</el-button>
            </div>
          </section>

          <section class="settings-card danger">
            <h2>清空数据</h2>
            <p class="hint">会删除题库、练习记录和错题本，无法恢复。</p>
            <el-button type="danger" :loading="clearing" @click="clearData">清空所有数据</el-button>
          </section>
        </main>
      </div>
    </div>

    <ProfileModal v-model:visible="showProfileModal" :username="username" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, List, Menu, Plus, Refresh, Setting } from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import { useUser } from '../composables/useUser'
import {
  clearAllData,
  deleteCustomAiKey,
  getSettings,
  saveCustomAiKey,
  saveDeepSeekKey,
  saveWrongThreshold,
  setAiProvider,
} from '../api'
import ProfileModal from '../components/ProfileModal.vue'
import { clearAuthSession } from '../utils/authStorage'

const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const { username, avatar, loadUserInfo } = useUser()

const showProfileModal = ref(false)
const settings = ref(null)
const wrongThreshold = ref(1)
const aiProvider = ref('platform')
const platformApiKey = ref('')
const customApiKey = ref('')
const savingThreshold = ref(false)
const savingPlatformKey = ref(false)
const savingCustomKey = ref(false)
const deletingCustomKey = ref(false)
const clearing = ref(false)

const loadSettings = async () => {
  settings.value = await getSettings()
  wrongThreshold.value = settings.value?.wrong_question_remove_threshold || 1
  aiProvider.value = settings.value?.ai_provider || 'platform'
}

const handleLogout = () => {
  clearAuthSession()
  router.push('/auth/login')
}

const saveThreshold = async () => {
  savingThreshold.value = true
  try {
    await saveWrongThreshold(wrongThreshold.value)
    ElMessage.success('已保存')
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    savingThreshold.value = false
  }
}

const savePlatformKey = async () => {
  if (!platformApiKey.value.trim()) return ElMessage.warning('请输入平台 API Key')
  savingPlatformKey.value = true
  try {
    await saveDeepSeekKey(platformApiKey.value.trim())
    platformApiKey.value = ''
    ElMessage.success('平台 Key 已保存')
    await loadSettings()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    savingPlatformKey.value = false
  }
}

const saveCustomKey = async () => {
  if (!customApiKey.value.trim()) return ElMessage.warning('请输入个人 API Key')
  savingCustomKey.value = true
  try {
    await saveCustomAiKey(customApiKey.value.trim())
    customApiKey.value = ''
    ElMessage.success('个人 Key 已保存')
    await loadSettings()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '保存失败')
  } finally {
    savingCustomKey.value = false
  }
}

const deleteCustomKey = async () => {
  deletingCustomKey.value = true
  try {
    await deleteCustomAiKey()
    ElMessage.success('个人 Key 已删除')
    await loadSettings()
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || '删除失败')
  } finally {
    deletingCustomKey.value = false
  }
}

const handleProviderChange = async (provider) => {
  try {
    await setAiProvider(provider)
    ElMessage.success('AI 来源已更新')
    await loadSettings()
  } catch (error) {
    aiProvider.value = settings.value?.ai_provider || 'platform'
    ElMessage.error(error?.response?.data?.detail || '切换失败')
  }
}

const copyInviteCode = async () => {
  try {
    await navigator.clipboard.writeText(settings.value?.invite_code || '')
    ElMessage.success('已复制邀请码')
  } catch {
    ElMessage.error('复制失败')
  }
}

const clearData = async () => {
  try {
    const { value: password } = await ElMessageBox.prompt('请输入当前登录密码', '确认清空', {
      inputType: 'password',
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      inputPlaceholder: '当前密码',
    })
    clearing.value = true
    await clearAllData(password)
    ElMessage.success('数据已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error?.response?.data?.detail || '清空失败')
    }
  } finally {
    clearing.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSettings(), loadUserInfo()])
})
</script>

<style scoped>
.app-layout { --sidebar-width: clamp(220px, 18vw, 256px); display: flex; min-height: 100vh; background: linear-gradient(135deg, rgba(184, 92, 56, 0.08) 0%, rgba(184, 92, 56, 0.04) 50%, rgba(139, 63, 31, 0.06) 100%); }
.sidebar { width: var(--sidebar-width); background: linear-gradient(180deg, #3d2f24 0%, #2c2416 100%); color: #f8f4ec; display: flex; flex-direction: column; flex: 0 0 var(--sidebar-width); min-height: 100vh; overflow: hidden; }
.logo-section { padding: 24px 20px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.logo-section h2 { margin: 0; font-size: 18px; }
.nav-menu { flex: 1; padding: 16px 12px; overflow-y: auto; }
.nav-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: 8px; cursor: pointer; color: #a89985; margin-bottom: 4px; }
.nav-item.active, .nav-item:hover { background: rgba(184, 92, 56, 0.14); color: #fff; }
.user-section { padding: 16px 20px; border-top: 1px solid rgba(255,255,255,0.1); }
.user-info { display: flex; align-items: center; gap: 12px; }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: rgba(255,255,255,0.12); display: flex; align-items: center; justify-content: center; font-weight: 700; }
.user-details { display: flex; flex-direction: column; gap: 4px; }
.logout-btn { font-size: 12px; color: #a89985; cursor: pointer; }
.main-content { flex: 1; min-width: 0; }
.settings-page { min-height: 100vh; }
.page-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 24px; background: #fff; border-bottom: 1px solid #e4e7ed; }
.page-header h1 { margin: 0 0 4px; font-size: 22px; }
.page-header p { margin: 0; color: #909399; font-size: 13px; }
.settings-content { max-width: 920px; margin: 24px auto; display: grid; gap: 16px; }
.settings-card { background: #fff; border: 1px solid #e4e7ed; border-radius: 14px; padding: 24px; }
.hero-card { background: linear-gradient(180deg, rgba(184, 92, 56, 0.08), rgba(255,255,255,0.92)); }
.hero-head, .card-title-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 16px; }
.eyebrow { margin: 0 0 6px; font-size: 12px; letter-spacing: 0.16em; color: #b85c38; }
.settings-card h2 { margin: 0; font-size: 20px; color: #303133; }
.stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.stat-box { background: #fff; border: 1px solid #ece7df; border-radius: 12px; padding: 14px; }
.stat-box span { display: block; font-size: 12px; color: #909399; margin-bottom: 8px; }
.stat-box strong { display: block; font-size: 18px; color: #303133; }
.field-block { margin-top: 16px; }
.field-block label { display: block; margin-bottom: 8px; font-size: 14px; font-weight: 600; color: #303133; }
.inline-row { display: flex; gap: 12px; align-items: center; }
.inline-row .el-input { flex: 1; }
.hint, .key-foot, .info-list { color: #909399; font-size: 13px; line-height: 1.7; }
.hint { margin: 8px 0 0; }
.key-foot { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 14px; }
.info-list { display: grid; gap: 8px; margin-top: 8px; }
.settings-card.danger h2 { color: #f56c6c; }
@media (max-width: 900px) { .stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 768px) { .inline-row { flex-direction: column; align-items: stretch; } .stats-grid { grid-template-columns: 1fr; } .hero-head, .card-title-row { flex-direction: column; align-items: flex-start; } }
</style>
