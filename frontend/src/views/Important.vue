<template>
  <div class="app-layout">
    <nav class="sidebar">
      <div class="logo-section">
        <svg class="logo-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 17L12 22L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M2 12L12 17L22 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
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
          <div class="avatar">👤</div>
          <div class="user-details">
            <span class="username">{{ username }}</span>
            <span class="logout-btn" @click="handleLogout">退出登录</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <div class="important-page">
        <header class="page-header">
          <div>
            <h1>重点题</h1>
            <p>这里汇总所有标星题目，可作为复习资料使用。</p>
          </div>
          <div class="header-actions">
            <el-select v-model="subjectId" clearable placeholder="全部科目" class="subject-select" @change="loadImportantQuestions">
              <el-option v-for="subject in subjects" :key="subject.id" :label="subject.name" :value="subject.id" />
            </el-select>
            <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
          </div>
        </header>

        <section class="table-panel">
          <el-table :data="importantList" border v-loading="loading" empty-text="暂无重点题">
            <el-table-column label="科目" width="130">
              <template #default="{ row }">{{ subjectName(row.subject_id) }}</template>
            </el-table-column>
            <el-table-column label="题型" width="90" align="center">
              <template #default="{ row }">{{ questionTypeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column label="题干" min-width="300">
              <template #default="{ row }">
                <div class="stem">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="答案" width="160">
              <template #default="{ row }">{{ displayAnswer(row) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="210" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="redoQuestion(row)">练习</el-button>
                <el-button size="small" type="warning" @click="unmarkImportant(row)">取消重点</el-button>
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
import { ElMessage } from 'element-plus'
import { Refresh, Document, Plus, Star, Setting, CircleClose, Delete } from '@element-plus/icons-vue'
import { getQuestions, getSubjects, updateQuestionImportant } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('auth_username') || '用户')
const subjects = ref([])
const subjectId = ref(null)
const importantList = ref([])
const loading = ref(false)

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

const subjectName = (id) => subjects.value.find((subject) => subject.id === id)?.name || '-'

const loadSubjects = async () => {
  subjects.value = await getSubjects()
}

const loadImportantQuestions = async () => {
  loading.value = true
  try {
    importantList.value = await getQuestions(0, 1000, subjectId.value, 'all', true)
  } catch (error) {
    ElMessage.error(`加载重点题失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const refreshAll = async () => {
  await loadSubjects()
  await loadImportantQuestions()
}

const redoQuestion = (row) => {
  router.push({ path: '/', query: { subject_id: row.subject_id, question_id: row.id } })
}

const unmarkImportant = async (row) => {
  try {
    await updateQuestionImportant(row.id, false)
    ElMessage.success('已取消重点标记')
    await loadImportantQuestions()
  } catch (error) {
    ElMessage.error(`取消失败：${error.response?.data?.detail || error.message}`)
  }
}

onMounted(refreshAll)
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
  font-size: 32px;
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

.important-page {
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

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subject-select {
  width: 180px;
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
