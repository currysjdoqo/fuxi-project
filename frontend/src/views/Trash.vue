<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
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
      <button
        v-if="!isMobileNav"
        type="button"
        class="desktop-sidebar-handle"
        :class="{ collapsed: sidebarCollapsed }"
        :aria-label="sidebarCollapsed ? '展开导航栏' : '隐藏导航栏'"
        @click="toggleSidebar"
      >
        {{ sidebarCollapsed ? '>' : '<' }}
      </button>
      <div class="trash-page">
        <header class="page-header">
          <el-button
            v-if="isMobileNav"
            circle
            text
            class="header-nav-btn"
            :icon="Menu"
            @click="toggleMobileNav"
          />
          <div>
            <h1>垃圾桶</h1>
            <p>删除的题目会先保留在这里，可以恢复；永久删除后不可找回。</p>
          </div>
          <div class="header-actions">
            <el-select v-model="subjectId" clearable placeholder="全部科目" class="subject-select" @change="loadTrash">
              <el-option v-for="subject in subjects" :key="subject.id" :label="subject.name" :value="subject.id" />
            </el-select>
            <el-button :icon="Refresh" @click="loadTrash">刷新</el-button>
          </div>
        </header>

        <section class="toolbar">
          <span>已选 {{ selectedIds.length }} / {{ trashList.length }}</span>
          <el-button size="small" @click="selectAll">全选</el-button>
          <el-button size="small" @click="selectedIds = []">清空</el-button>
          <el-button size="small" type="success" :disabled="!selectedIds.length" :loading="restoring" @click="restoreSelected">
            恢复选中
          </el-button>
          <el-button size="small" type="danger" :disabled="!selectedIds.length" :loading="deleting" @click="permanentDeleteSelected">
            彻底删除选中
          </el-button>
        </section>

        <section class="table-panel">
          <el-table :data="trashList" border v-loading="loading" empty-text="垃圾桶为空">
            <el-table-column width="52" align="center">
              <template #default="{ row }">
                <el-checkbox :model-value="selectedIds.includes(row.id)" @change="toggleSelection(row.id)" />
              </template>
            </el-table-column>
            <el-table-column prop="subject_name" label="科目" width="130" />
            <el-table-column label="题型" width="90" align="center">
              <template #default="{ row }">{{ questionTypeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column label="题干" min-width="280">
              <template #default="{ row }">
                <div class="stem">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="答案" width="150">
              <template #default="{ row }">{{ displayAnswer(row) }}</template>
            </el-table-column>
            <el-table-column label="删除时间" width="180">
              <template #default="{ row }">{{ formatDate(row.deleted_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="restoreOne(row.id)">恢复</el-button>
                <el-button size="small" type="danger" @click="permanentDelete(row.id)">永久删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleClose, Delete, Document, List, Menu, Plus, Refresh, Setting, Star } from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import {
  getSubjects,
  getTrashQuestions,
  permanentlyDeleteQuestion,
  permanentlyDeleteTrashQuestions,
  restoreTrashQuestions
} from '../api'

const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const username = ref(localStorage.getItem('auth_username') || '用户')
const subjects = ref([])
const subjectId = ref(null)
const trashList = ref([])
const selectedIds = ref([])
const loading = ref(false)
const restoring = ref(false)
const deleting = ref(false)

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const questionTypeLabel = (type) => ({
  single: '单选题',
  multi: '多选题',
  judge: '判断题',
  fill: '填空题',
  short: '简答题',
  code: '编程题'
}[type] || '题目')

const displayAnswer = (row) => {
  if (row.type === 'judge') {
    return row.answer === 'T' ? '正确' : row.answer === 'F' ? '错误' : row.answer
  }
  if (row.type === 'multi') {
    return row.answer.split('').join('、')
  }
  return row.answer
}

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const loadSubjects = async () => {
  subjects.value = await getSubjects()
}

const loadTrash = async () => {
  loading.value = true
  try {
    trashList.value = await getTrashQuestions(subjectId.value)
    selectedIds.value = selectedIds.value.filter((id) => trashList.value.some((item) => item.id === id))
  } catch (error) {
    ElMessage.error(`加载垃圾桶失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (questionId) => {
  if (selectedIds.value.includes(questionId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== questionId)
    return
  }
  selectedIds.value = [...selectedIds.value, questionId]
}

const selectAll = () => {
  selectedIds.value = trashList.value.map((item) => item.id)
}

const restoreSelected = async () => {
  if (!selectedIds.value.length) return
  restoring.value = true
  try {
    await restoreTrashQuestions(selectedIds.value)
    ElMessage.success('题目已恢复')
    selectedIds.value = []
    await loadTrash()
  } catch (error) {
    ElMessage.error(`恢复失败：${error.response?.data?.detail || error.message}`)
  } finally {
    restoring.value = false
  }
}

const restoreOne = async (questionId) => {
  selectedIds.value = [questionId]
  await restoreSelected()
}

const permanentDeleteSelected = async () => {
  if (!selectedIds.value.length) return

  try {
    await ElMessageBox.confirm(
      `确认彻底删除选中的 ${selectedIds.value.length} 道题？该操作不可恢复。`,
      '彻底删除',
      {
        type: 'warning',
        confirmButtonText: '彻底删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await permanentlyDeleteTrashQuestions(selectedIds.value)
    ElMessage.success('选中题目已彻底删除')
    selectedIds.value = []
    await loadTrash()
  } catch (error) {
    ElMessage.error(`批量彻底删除失败：${error.response?.data?.detail || error.message}`)
  } finally {
    deleting.value = false
  }
}

const permanentDelete = async (questionId) => {
  try {
    await ElMessageBox.confirm('确认永久删除这道题？该操作不可恢复。', '永久删除', {
      type: 'warning',
      confirmButtonText: '永久删除',
      cancelButtonText: '取消'
    })
    await permanentlyDeleteQuestion(questionId)
    ElMessage.success('题目已永久删除')
    selectedIds.value = selectedIds.value.filter((id) => id !== questionId)
    await loadTrash()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`永久删除失败：${error.response?.data?.detail || error.message}`)
    }
  }
}

onMounted(async () => {
  await loadSubjects()
  await loadTrash()
})
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

.trash-page {
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

.header-actions,
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subject-select {
  width: 180px;
}

.toolbar {
  padding: 14px 20px 0;
}

.toolbar span {
  color: #606266;
}

.table-panel {
  padding: 20px;
}

.stem {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #606266;
}
</style>
