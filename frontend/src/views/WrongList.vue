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
      <div class="wrong-page">
        <header class="page-header">
          <div>
            <h1>{{ selectedSubject ? `${selectedSubject.name}错题本` : '错题本' }}</h1>
            <p>错题按来源科目自动归类，最近一次错误答案来自练习记录。</p>
          </div>
          <div class="header-actions">
            <el-button :icon="Refresh" @click="refreshAll">刷新</el-button>
            <el-button type="success" :icon="Collection" @click="openReviewDialog">随机复习</el-button>
          </div>
        </header>

        <section class="book-grid">
          <button
            v-for="subject in subjects"
            :key="subject.id"
            class="book-card"
            :class="{ active: selectedSubjectId === subject.id, empty: !subject.wrong_count }"
            @click="selectSubject(subject)"
          >
            <strong>{{ subject.name }}</strong>
            <span>{{ subject.wrong_count || 0 }} 道错题</span>
            <small>共 {{ subject.question_count || 0 }} 道题</small>
          </button>
          <el-empty v-if="!subjects.length" description="暂无科目" />
        </section>

        <section class="table-panel">
          <el-table :data="wrongList" border v-loading="loading" :empty-text="selectedSubject ? '当前错题本暂无错题' : '请选择错题本'">
            <el-table-column label="题干" min-width="260">
              <template #default="{ row }">
                <div class="stem">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="题型" width="90" align="center">
              <template #default="{ row }">
                {{ questionTypeLabel(row.type) }}
              </template>
            </el-table-column>
            <el-table-column label="正确答案" width="120" align="center">
              <template #default="{ row }">
                {{ displayAnswer(row) }}
              </template>
            </el-table-column>
            <el-table-column label="你的错误答案" width="130" align="center">
              <template #default="{ row }">
                <el-tag type="danger" v-if="row.last_user_answer">{{ row.last_user_answer }}</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="解析" min-width="260">
              <template #default="{ row }">
                <div class="explanation">{{ row.explanation || '-' }}</div>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" :icon="Edit" @click="redoQuestion(row)">重做</el-button>
                <el-button size="small" type="danger" :icon="Delete" @click="removeQuestion(row.question_id)">移除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <el-dialog v-model="reviewDialogVisible" title="随机复习" width="360px">
          <div class="dialog-line">
            <span>抽取数量</span>
            <el-input-number v-model="reviewCount" :min="1" :max="Math.max(wrongList.length, 1)" />
          </div>
          <template #footer>
            <el-button @click="reviewDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="startReview">开始</el-button>
          </template>
        </el-dialog>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Refresh, Collection, Document, Plus, Star, Setting, CircleClose } from '@element-plus/icons-vue'
import { removeWrongQuestion, getSubjects, getWrongQuestions } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('auth_username') || '用户')
const loading = ref(false)
const subjects = ref([])
const selectedSubjectId = ref(null)
const wrongList = ref([])
const reviewDialogVisible = ref(false)
const reviewCount = ref(10)

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const selectedSubject = computed(() => {
  return subjects.value.find(s => s.id === selectedSubjectId.value)
})

const questionTypeLabel = (type) => {
  return { single: '单选题', multi: '多选题', judge: '判断题', fill: '填空题', short: '简答题', code: '编程题' }[type] || type
}

const displayAnswer = (question) => {
  if (question.type === 'judge') return question.answer === 'T' ? '正确' : question.answer === 'F' ? '错误' : question.answer
  if (question.type === 'multi') return question.answer.split('').join('、')
  return question.answer
}

const refreshAll = async () => {
  loading.value = true
  try {
    subjects.value = await getSubjects()
    if (selectedSubjectId.value) await loadWrongList()
  } catch (error) {
    ElMessage.error(`刷新失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const loadWrongList = async () => {
  if (!selectedSubjectId.value) return
  loading.value = true
  try {
    wrongList.value = await getWrongQuestions(selectedSubjectId.value)
  } catch (error) {
    ElMessage.error(`加载错题本失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const selectSubject = async (subject) => {
  if (selectedSubjectId.value === subject.id) {
    selectedSubjectId.value = null
    wrongList.value = []
    return
  }
  selectedSubjectId.value = subject.id
  await loadWrongList()
}

const redoQuestion = (wrong) => {
  router.push({ path: '/', query: { question_id: wrong.question_id, subject_id: selectedSubjectId.value } })
}

const removeQuestion = async (questionId) => {
  try {
    await ElMessageBox.confirm('确认将本题从错题本移除？', '移除错题', { type: 'warning' })
    await removeWrongQuestion(questionId)
    ElMessage.success('已移出错题本')
    await Promise.all([loadWrongList(), refreshAll()])
  } catch (error) {
    if (error !== 'cancel') ElMessage.error(`移出错题本失败：${error.response?.data?.detail || error.message}`)
  }
}

const openReviewDialog = () => {
  if (!wrongList.value.length) {
    ElMessage.warning('暂无错题可复习')
    return
  }
  reviewCount.value = Math.min(10, wrongList.value.length)
  reviewDialogVisible.value = true
}

const startReview = () => {
  router.push({
    path: '/review',
    query: { subject_id: selectedSubjectId.value, count: reviewCount.value }
  })
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

.wrong-page {
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
  gap: 10px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
  padding: 20px 24px;
}

.book-card {
  display: grid;
  gap: 6px;
  padding: 18px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  text-align: left;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.book-card:hover {
  border-color: #3b82f6;
}

.book-card.active {
  border-color: #3b82f6;
  background: #eff6ff;
}

.book-card.empty {
  opacity: 0.6;
}

.book-card strong {
  font-size: 16px;
  color: #303133;
}

.book-card span {
  color: #909399;
}

.book-card small {
  color: #c0c4cc;
}

.table-panel {
  padding: 0 24px 24px;
}

.stem, .explanation {
  line-height: 1.6;
  word-break: break-all;
}

.dialog-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
</style>
