<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
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
      <div class="review-page">
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
            <h1>复习模式</h1>
            <p>答对会自动移出错题本，答错会继续保留。</p>
          </div>
          <el-button :icon="Back" @click="$router.push({ path: '/wrong', query: subjectId ? { subject_id: subjectId } : {} })">返回错题本</el-button>
        </header>

        <main class="review-content">
          <section v-if="!reviewStarted" class="start-card">
            <div class="count-row">
              <span>复习科目</span>
              <el-select v-model="subjectId" placeholder="请选择科目" class="subject-select">
                <el-option
                  v-for="subject in subjects"
                  :key="subject.id"
                  :label="`${subject.name}（${subject.wrong_count || 0} 道错题）`"
                  :value="subject.id"
                  :disabled="!subject.wrong_count"
                />
              </el-select>
            </div>
            <div class="count-row">
              <span>抽取数量</span>
              <el-input-number v-model="reviewCount" :min="1" :max="maxReviewCount" />
            </div>
            <el-button type="primary" size="large" :icon="Collection" :loading="isGenerating" @click="startReview">
              开始复习
            </el-button>
          </section>

          <section v-else-if="reviewFinished" class="summary-card">
            <h2>复习完成</h2>
            <div class="summary-grid">
              <div>
                <strong>{{ correctCount }}</strong>
                <span>正确</span>
              </div>
              <div>
                <strong>{{ reviewQuestions.length - correctCount }}</strong>
                <span>错误</span>
              </div>
              <div>
                <strong>{{ accuracyPercent }}%</strong>
                <span>正确率</span>
              </div>
            </div>
            <div class="summary-actions">
              <el-button type="primary" :icon="Refresh" @click="restartReview">再来一轮</el-button>
              <el-button @click="$router.push({ path: '/wrong', query: subjectId ? { subject_id: subjectId } : {} })">返回错题本</el-button>
            </div>
          </section>

          <section v-else-if="currentQuestion" class="question-card">
            <el-progress :percentage="progressPercent" :show-text="false" />
            <div class="progress-text">第 {{ currentIndex + 1 }} / {{ reviewQuestions.length }} 题</div>

            <div class="question-content">{{ currentQuestion.content }}</div>

            <el-radio-group v-if="isOptionQuestion && !isMultiQuestion" v-model="selectedAnswer" class="options" :disabled="showResult">
              <label
                v-for="item in answerOptions"
                :key="item.key"
                class="option-item"
                :class="{
                  correct: showResult && item.key === currentQuestion.answer,
                  wrong: showResult && selectedAnswer === item.key && !currentResult?.is_correct
                }"
              >
                <el-radio :label="item.key">
                  <span class="option-key">{{ item.key }}</span>
                  <span>{{ item.value }}</span>
                </el-radio>
              </label>
            </el-radio-group>

            <el-checkbox-group v-else-if="isMultiQuestion" v-model="selectedAnswerList" class="options" :disabled="showResult">
              <label
                v-for="item in answerOptions"
                :key="item.key"
                class="option-item"
                :class="{
                  correct: showResult && currentMultiAnswerSet.has(item.key),
                  wrong: showResult && selectedAnswerList.includes(item.key) && !currentMultiAnswerSet.has(item.key)
                }"
              >
                <el-checkbox :label="item.key">
                  <span class="option-key">{{ item.key }}</span>
                  <span>{{ item.value }}</span>
                </el-checkbox>
              </label>
            </el-checkbox-group>

            <div v-else class="answer-input-wrap">
              <el-input
                v-model="selectedAnswer"
                :type="['short', 'code'].includes(currentQuestion.type) ? 'textarea' : 'text'"
                :rows="currentQuestion.type === 'code' ? 8 : currentQuestion.type === 'short' ? 5 : 1"
                placeholder="请输入你的答案"
                :disabled="showResult"
              />
            </div>

            <div v-if="showResult" :class="['result-wrap', currentResult?.is_correct ? 'correct' : 'wrong']">
              <strong>{{ currentResult?.is_correct ? '回答正确，已移出错题本' : '回答错误，继续保留错题本' }}</strong>
              <span>参考答案：{{ displayAnswer(currentQuestion) }}</span>
            </div>

            <div class="action-bar">
              <el-button :icon="Back" :disabled="currentIndex <= 0" @click="prevQuestion">上一题</el-button>
              <template v-if="!showResult">
                <el-button type="primary" :icon="Check" :loading="submitting" :disabled="!selectedAnswer" @click="submitAnswer">
                  提交答案
                </el-button>
              </template>
              <template v-else>
                <el-button type="primary" :icon="ArrowRight" @click="nextQuestion">
                  {{ currentIndex < reviewQuestions.length - 1 ? '下一题' : '完成' }}
                </el-button>
              </template>
            </div>
          </section>
        </main>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Back, Check, Collection, Refresh, Document, Plus, Star, Setting, CircleClose, Delete, Menu } from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import { generateReviewQuestions, getSubjects, submitReviewAnswer } from '../api'

const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const route = useRoute()
const username = ref(localStorage.getItem('auth_username') || '用户')
const reviewStarted = ref(false)
const reviewFinished = ref(false)
const isGenerating = ref(false)
const submitting = ref(false)
const reviewCount = ref(10)
const subjectId = ref(null)
const subjects = ref([])
const reviewQuestions = ref([])
const currentIndex = ref(0)
const answers = ref({})
const showResult = ref(false)
const currentResult = ref(null)

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const currentQuestion = computed(() => reviewQuestions.value[currentIndex.value])
const currentQuestionId = computed(() => currentQuestion.value?.id ?? currentQuestion.value?.question_id ?? null)
const selectedSubject = computed(() => subjects.value.find((item) => item.id === subjectId.value) || null)
const maxReviewCount = computed(() => {
  const wrongCount = selectedSubject.value?.wrong_count || 0
  return Math.max(1, Math.min(50, wrongCount || 1))
})
const correctCount = computed(() => Object.values(answers.value).filter(a => a.is_correct).length)
const accuracyPercent = computed(() => reviewQuestions.value.length ? Math.round((correctCount.value / reviewQuestions.value.length) * 100) : 0)
const progressPercent = computed(() => Math.round(((currentIndex.value) / reviewQuestions.value.length) * 100))

const selectedAnswer = ref('')
const selectedAnswerList = computed({
  get: () => {
    if (!currentQuestion.value || currentQuestion.value.type !== 'multi') return []
    return selectedAnswer.value ? selectedAnswer.value.split('').filter(Boolean) : []
  },
  set: (val) => {
    selectedAnswer.value = Array.isArray(val) ? val.sort().join('') : ''
  }
})

const isOptionQuestion = computed(() => ['single', 'multi', 'judge'].includes(currentQuestion.value?.type))
const isMultiQuestion = computed(() => currentQuestion.value?.type === 'multi')

const answerOptions = computed(() => {
  if (!currentQuestion.value) return []
  if (currentQuestion.value.type === 'judge') {
    return [
      { key: 'T', value: currentQuestion.value.options?.T || '正确' },
      { key: 'F', value: currentQuestion.value.options?.F || '错误' }
    ]
  }
  return Object.keys(currentQuestion.value.options || {}).sort().map(key => ({
    key,
    value: currentQuestion.value.options[key]
  }))
})

const currentMultiAnswerSet = computed(() => new Set(currentQuestion.value?.answer ? currentQuestion.value.answer.split('').filter(Boolean) : []))

const loadSubjects = async () => {
  try {
    subjects.value = await getSubjects()
    if (subjectId.value && !selectedSubject.value) {
      subjectId.value = null
    }
    if (!subjectId.value && subjects.value.length === 1) {
      subjectId.value = subjects.value[0].id
    }
    if (reviewCount.value > maxReviewCount.value) {
      reviewCount.value = maxReviewCount.value
    }
  } catch (error) {
    ElMessage.error(`鍔犺浇绉戠洰澶辫触锛?{error.response?.data?.detail || error.message}`)
  }
}

const syncReviewCountWithSubject = () => {
  if (reviewCount.value > maxReviewCount.value) {
    reviewCount.value = maxReviewCount.value
  }
  if (reviewCount.value < 1) {
    reviewCount.value = 1
  }
}

const displayAnswer = (question) => {
  if (question.type === 'judge') return question.answer === 'T' ? '正确' : question.answer === 'F' ? '错误' : question.answer
  if (question.type === 'multi') return question.answer.split('').join('、')
  return question.answer
}

const startReview = async () => {
  if (!subjectId.value) {
    ElMessage.warning('璇峰厛閫夋嫨涓€涓鐩啀寮€濮嬪涔?')
    return
  }
  isGenerating.value = true
  try {
    const count = Number(reviewCount.value) || 10
    const generatedQuestions = await generateReviewQuestions(count, subjectId.value)
    reviewQuestions.value = generatedQuestions.map(question => ({
      ...question,
      id: question.id ?? question.question_id
    }))
    if (!reviewQuestions.value.length) {
      ElMessage.warning('褰撳墠绉戠洰鏆傛棤鍙涔犵殑閿欓')
      return
    }
    reviewStarted.value = true
    currentIndex.value = 0
    answers.value = {}
    showResult.value = false
    currentResult.value = null
    selectedAnswer.value = ''
  } catch (error) {
    ElMessage.error(`生成复习题失败：${error.response?.data?.detail || error.message}`)
  } finally {
    isGenerating.value = false
  }
}

const submitAnswer = async () => {
  if (!selectedAnswer.value || !currentQuestionId.value) return
  submitting.value = true
  try {
    const result = await submitReviewAnswer(currentQuestionId.value, selectedAnswer.value)
    const savedResult = {
      ...result,
      user_answer: selectedAnswer.value
    }
    currentResult.value = savedResult
    answers.value[currentQuestionId.value] = savedResult
    showResult.value = true
  } catch (error) {
    ElMessage.error(`提交答案失败：${error.response?.data?.detail || error.message}`)
  } finally {
    submitting.value = false
  }
}

const nextQuestion = () => {
  if (currentIndex.value < reviewQuestions.value.length - 1) {
    currentIndex.value += 1
    showResult.value = false
    selectedAnswer.value = ''
  } else {
    reviewFinished.value = true
  }
}

const prevQuestion = () => {
  if (currentIndex.value > 0) {
    currentIndex.value -= 1
    const previousQuestionId = reviewQuestions.value[currentIndex.value]?.id
    const previous = previousQuestionId ? answers.value[previousQuestionId] : null
    if (previous) {
      showResult.value = true
      selectedAnswer.value = previous.user_answer
      currentResult.value = previous
    } else {
      showResult.value = false
      selectedAnswer.value = ''
    }
  }
}

const restartReview = () => {
  reviewStarted.value = false
  reviewFinished.value = false
  reviewQuestions.value = []
  currentIndex.value = 0
  answers.value = {}
  showResult.value = false
  selectedAnswer.value = ''
  subjectId.value = route.query.subject_id ? Number(route.query.subject_id) : null
  reviewCount.value = route.query.count ? Number(route.query.count) : Math.min(10, maxReviewCount.value)
}

watch(subjectId, () => {
  syncReviewCountWithSubject()
})

onMounted(async () => {
  if (route.query.subject_id) subjectId.value = Number(route.query.subject_id)
  if (route.query.count) reviewCount.value = Number(route.query.count)
  await loadSubjects()
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

.review-page {
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

.review-content {
  max-width: 720px;
  margin: 24px auto;
}

.start-card, .summary-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  display: grid;
  gap: 24px;
}

.count-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.count-row span {
  color: #606266;
}

.summary-card h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.summary-grid div {
  display: grid;
  gap: 8px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 8px;
}

.summary-grid div strong {
  font-size: 32px;
  color: #303133;
}

.summary-grid div span {
  color: #909399;
}

.summary-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.question-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
}

.progress-text {
  text-align: center;
  margin: 8px 0 24px;
  color: #909399;
  font-size: 13px;
}

.question-content {
  font-size: 18px;
  line-height: 1.7;
  color: #303133;
  margin-bottom: 24px;
  white-space: pre-wrap;
}

.options {
  display: grid;
  gap: 12px;
}

.option-item {
  padding: 14px 18px;
  border: 2px solid #e4e7ed;
  border-radius: 8px;
  transition: all 0.2s ease;
  cursor: pointer;
}

.option-item:hover {
  border-color: #c0c4cc;
}

.option-item.correct {
  border-color: #67c23a;
  background: #f0f9eb;
}

.option-item.wrong {
  border-color: #f56c6c;
  background: #fef0f0;
}

.option-key {
  font-weight: 700;
  margin-right: 10px;
}

.result-wrap {
  margin: 24px 0;
  padding: 16px;
  border-radius: 8px;
  display: grid;
  gap: 8px;
}

.result-wrap.correct {
  background: #f0f9eb;
  border: 1px solid #e1f3d8;
  color: #67c23a;
}

.result-wrap.wrong {
  background: #fef0f0;
  border: 1px solid #fde2e2;
  color: #f56c6c;
}

.action-bar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
}

.action-bar .el-button {
  flex: 0.6;
}
</style>
