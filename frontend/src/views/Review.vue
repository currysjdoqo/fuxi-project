<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
    <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, open: mobileNavOpen }">
      <div class="logo-section">
        <div class="logo-group">
          <el-icon class="logo-icon"><Document /></el-icon>
          <div class="logo-copy">
            <h2>习题管理系统</h2>
            <span>Practice Workspace</span>
          </div>
        </div>
        <el-button
          v-if="isMobileNav"
          circle
          text
          class="sidebar-toggle mobile-close"
          :icon="Close"
          @click="closeMobileNav"
        />
      </div>

      <div class="nav-menu">
        <div class="nav-section-title">功能导航</div>
        <div
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          @click="goToPath(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </div>

      <div class="user-section">
        <div class="user-info">
          <div class="avatar" :style="{ background: avatar ? `url(${avatar}) center/cover` : undefined }" @click="showProfileModal = true">
            <template v-if="!avatar">{{ username.charAt(0).toUpperCase() }}</template>
          </div>
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
      <div class="practice-page">
        <header class="page-header">
          <div class="header-main">
            <div class="header-nav">
              <el-button
                v-if="isMobileNav"
                circle
                text
                class="header-nav-btn"
                :icon="Menu"
                @click="toggleMobileNav()"
              />
              <div v-if="selectedSubject" class="subject-chip">
                <el-icon><Document /></el-icon>
                <span>{{ selectedSubject.name }}</span>
              </div>
            </div>
            <h1>{{ selectedSubject ? `${selectedSubject.name} - 复习模式` : '选择科目' }}</h1>
            <p>{{ selectedSubject ? '复习错题，巩固知识。答对会自动移出错题本。' : '先选择一个科目，然后开始复习错题。' }}</p>
          </div>
          <div class="header-actions">
            <el-button v-if="selectedSubject" :icon="Back" @click="backToSubjects">返回科目</el-button>
            <el-button v-if="selectedSubject" :icon="Refresh" @click="resetReview">重新开始</el-button>
          </div>
        </header>

        <main v-if="!selectedSubject" class="subject-page">
          <div v-if="loading" class="loading-wrapper">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
          <div v-else class="subject-grid">
            <div
              v-for="subject in subjects"
              :key="subject.id"
              class="subject-card"
              @click="handleSubjectClick(subject)"
            >
              <div class="subject-icon">
                <el-icon><component :is="getSubjectIcon(subject.name)" /></el-icon>
              </div>
              <div class="subject-info">
                <h3>{{ subject.name }}</h3>
                <p>{{ subject.wrong_count || 0 }} 道错题</p>
                <div v-if="subject.wrong_count" class="review-mode-selection">
                  <el-radio-group 
                    :model-value="reviewModes[subject.id] || 'sequential'" 
                    @update:model-value="(mode) => updateReviewMode(subject.id, mode)"
                    size="small"
                  >
                    <el-radio-button label="sequential">顺序复习</el-radio-button>
                    <el-radio-button label="range">范围复习</el-radio-button>
                    <el-radio-button label="random">随机抽题</el-radio-button>
                  </el-radio-group>
                  
                  <template v-if="(reviewModes[subject.id] || 'sequential') === 'range'">
                    <div class="range-controls">
                      <el-input-number
                        :model-value="reviewStartIndices[subject.id] || 1"
                        @update:model-value="(val) => reviewStartIndices[subject.id] = val"
                        :min="1"
                        :max="subject.wrong_count"
                        :step="1"
                        controls-position="right"
                        size="small"
                      />
                      <span>-</span>
                      <el-input-number
                        :model-value="reviewEndIndices[subject.id] || Math.min(10, subject.wrong_count)"
                        @update:model-value="(val) => reviewEndIndices[subject.id] = val"
                        :min="(reviewStartIndices[subject.id] || 1)"
                        :max="subject.wrong_count"
                        :step="1"
                        controls-position="right"
                        size="small"
                      />
                    </div>
                  </template>
                  <template v-else>
                    <el-input-number
                      :model-value="reviewQuestionCounts[subject.id] || Math.min(10, subject.wrong_count)"
                      @update:model-value="(val) => reviewQuestionCounts[subject.id] = val"
                      :min="1"
                      :max="subject.wrong_count"
                      :step="1"
                      controls-position="right"
                      size="small"
                    />
                  </template>
                </div>
                <el-button type="primary" :disabled="!subject.wrong_count" @click="startReview(subject)">开始复习</el-button>
              </div>
            </div>
          </div>
        </main>

        <main v-else class="practice-main">
          <div class="practice-sidebar">
            <div class="sidebar-stats">
              <div class="stat-item">
                <span class="stat-label">已完成</span>
                <span class="stat-value">{{ completedCount }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">正确率</span>
                <span class="stat-value">{{ accuracyPercent }}%</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">待提交</span>
                <span class="stat-value">{{ pendingSubmissions.length }}</span>
              </div>
            </div>
            <div class="question-nav">
              <div
                v-for="(q, index) in questions"
                :key="q.id"
                class="question-dot"
                :class="{
                  'active': index === currentIndex,
                  'answered': answers[index] && !answers[index].isPending,
                  'pending': answers[index]?.isPending,
                  'correct': answers[index]?.isCorrect === true,
                  'wrong': answers[index]?.isCorrect === false
                }"
                @click="selectQuestion(index)"
              >
                {{ index + 1 }}
              </div>
            </div>
            <el-button
              v-if="pendingSubmissions.length > 0"
              type="primary"
              :loading="batchSubmitting"
              @click="submitAllPending"
              class="batch-submit-btn"
            >
              {{ batchSubmitting ? '提交中...' : `批量提交 (${pendingSubmissions.length})` }}
            </el-button>
          </div>

          <div class="question-content">
            <div v-if="currentQuestion" class="question-card">
              <div class="question-header">
                <span class="question-number">第 {{ currentIndex + 1 }} 题</span>
                <span class="question-type-badge" :class="`type-${currentQuestion.type}`">
                  {{ getQuestionTypeName(currentQuestion.type) }}
                </span>
              </div>

              <div class="question-text">{{ currentQuestion.content }}</div>

              <el-radio-group
                v-if="isOptionQuestion && !isMultiQuestion"
                v-model="selectedAnswer"
                class="options"
                :disabled="hasAnswered"
              >
                <label
                  v-for="item in answerOptions"
                  :key="item.key"
                  class="option-item"
                  :class="{
                    'selected': selectedAnswer === item.key,
                    'correct': showResult && item.key === currentQuestion.answer,
                    'wrong': showResult && selectedAnswer === item.key && !currentResult?.isCorrect
                  }"
                >
                  <el-radio :label="item.key">
                    <span class="option-key">{{ item.key }}</span>
                    <span>{{ item.value }}</span>
                  </el-radio>
                </label>
              </el-radio-group>

              <el-checkbox-group
                v-else-if="isMultiQuestion"
                v-model="selectedAnswerList"
                class="options"
                :disabled="hasAnswered"
              >
                <label
                  v-for="item in answerOptions"
                  :key="item.key"
                  class="option-item"
                  :class="{
                    'selected': selectedAnswerList.includes(item.key),
                    'correct': showResult && currentMultiAnswerSet.has(item.key),
                    'wrong': showResult && selectedAnswerList.includes(item.key) && !currentMultiAnswerSet.has(item.key)
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
                  :disabled="hasAnswered"
                />
              </div>

              <div v-if="showResult" :class="['result-box', resultBoxClass]">
                <div class="result-icon">
                  <el-icon v-if="currentResult?.isCorrect === true"><SuccessFilled /></el-icon>
                  <el-icon v-else><CircleCloseFilled /></el-icon>
                </div>
                <div class="result-content">
                  <h3>{{ resultTitle }}</h3>
                  <p v-if="currentQuestion.answer">参考答案：{{ resultTitle }}</p>
                </div>
              </div>

              <div v-if="showSelfEvaluationActions" class="self-evaluation-actions">
                <el-button type="success" size="large" @click="submitSelfEvaluation(true)">
                  <el-icon><SuccessFilled /></el-icon>
                  我答对了
                </el-button>
                <el-button type="danger" size="large" @click="submitSelfEvaluation(false)">
                  <el-icon><CircleCloseFilled /></el-icon>
                  我答错了
                </el-button>
              </div>

              <div class="action-buttons">
                <el-button :disabled="currentIndex === 0" @click="selectQuestion(currentIndex - 1)">
                  上一题
                </el-button>
                <el-button
                  v-if="!hasAnswered"
                  type="primary"
                  :disabled="!selectedAnswer"
                  @click="submitCurrentAnswer"
                >
                  提交答案
                </el-button>
                <el-button
                  v-else
                  type="primary"
                  @click="selectQuestion(currentIndex + 1)"
                  :disabled="currentIndex === questions.length - 1"
                >
                  下一题
                </el-button>
                <el-button :icon="ChatDotRound" :loading="aiLoading" @click="loadAiExplanation">
                  AI讲解
                </el-button>
              </div>

              <!-- AI 讲解内容 -->
              <div v-if="aiExplanation" class="explanation-box ai">
                <h3>AI 讲解</h3>
                <div class="explanation-content" v-html="renderedExplanation"></div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>

    <ProfileModal
      v-model:visible="showProfileModal"
      :username="username"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProfileModal from '../components/ProfileModal.vue'
import {
  Document,
  List,
  Plus,
  CircleClose,
  Refresh,
  Star,
  Delete,
  Setting,
  Menu,
  Close,
  Back,
  Loading,
  SuccessFilled,
  CircleCloseFilled,
  ChatDotRound
} from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import { useUser } from '../composables/useUser'
import { getSubjects, getWrongQuestions, submitReviewAnswer, batchSubmitReviewAnswers, getAiExplanation } from '../api'

const router = useRouter()
const route = useRoute()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const { username, avatar } = useUser()

const showProfileModal = ref(false)
const loading = ref(false)
const subjects = ref([])
const selectedSubject = ref(null)
const questions = ref([])
const currentIndex = ref(0)
const selectedAnswer = ref('')
const answers = ref({})
const showResult = ref(false)
const showExplanation = ref(false)
const currentResult = ref(null)
const pendingSubmissions = ref([])
const batchSubmitting = ref(false)
const aiLoading = ref(false)
const aiExplanation = ref('')

const reviewModes = ref({})
const reviewQuestionCounts = ref({})
const reviewStartIndices = ref({})
const reviewEndIndices = ref({})

const currentReviewMode = computed(() => {
  return selectedSubject.value ? reviewModes.value[selectedSubject.value.id] || 'sequential' : 'sequential'
})

const currentReviewQuestionCount = computed({
  get: () => {
    return selectedSubject.value ? reviewQuestionCounts.value[selectedSubject.value.id] || 10 : 10
  },
  set: (value) => {
    if (selectedSubject.value) {
      reviewQuestionCounts.value[selectedSubject.value.id] = value
    }
  }
})

const currentReviewStartIndex = computed({
  get: () => {
    return selectedSubject.value ? reviewStartIndices.value[selectedSubject.value.id] || 1 : 1
  },
  set: (value) => {
    if (selectedSubject.value) {
      reviewStartIndices.value[selectedSubject.value.id] = value
    }
  }
})

const currentReviewEndIndex = computed({
  get: () => {
    return selectedSubject.value ? reviewEndIndices.value[selectedSubject.value.id] || 10 : 10
  },
  set: (value) => {
    if (selectedSubject.value) {
      reviewEndIndices.value[selectedSubject.value.id] = value
    }
  }
})

const updateReviewMode = (subjectId, mode) => {
  reviewModes.value[subjectId] = mode
}

const navItems = [
  { path: '/', label: '练习模式', icon: Document },
  { path: '/plan', label: '学习计划', icon: List },
  { path: '/import', label: '导入习题', icon: Plus },
  { path: '/wrong', label: '错题本', icon: CircleClose },
  { path: '/review', label: '复习模式', icon: Refresh },
  { path: '/important', label: '重点题', icon: Star },
  { path: '/trash', label: '垃圾桶', icon: Delete },
  { path: '/settings', label: '设置', icon: Setting },
]

const goToPath = (path) => {
  if (route.path === path) return
  if (isMobileNav.value) {
    mobileNavOpen.value = false
  }
  router.push(path)
}

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const currentQuestion = computed(() => questions.value[currentIndex.value])
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
const currentMultiAnswerSet = computed(() => new Set((currentQuestion.value?.answer || '').split('').filter(Boolean)))
const currentAnswerState = computed(() => answers.value[currentIndex.value] || null)
const showSelfEvaluationActions = computed(() => Boolean(currentAnswerState.value?.isPending))
const resultBoxClass = computed(() => {
  if (!showResult.value) return ''
  if (currentAnswerState.value?.isPending) return 'pending'
  return currentAnswerState.value?.isCorrect ? 'correct' : 'wrong'
})
const resultTitle = computed(() => {
  if (currentAnswerState.value?.isPending) return '请自行判断是否答对'
  if (currentAnswerState.value?.isCorrect === true) return '回答正确，已从错题本移除'
  if (currentAnswerState.value?.isCorrect === false) return '回答错误，继续保留错题本'
  return '提交中...'
})
const hasAnswered = computed(() => answers.value[currentIndex.value] !== undefined)

// 简单的 Markdown 渲染
const renderedExplanation = computed(() => {
  if (!aiExplanation.value) return ''
  let html = aiExplanation.value
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return html
})
const completedCount = computed(() => Object.values(answers.value).filter((item) => !item.isPending).length)
const accuracyPercent = computed(() => {
  const completed = completedCount.value
  if (completed === 0) return 0
  const correct = Object.values(answers.value).filter((item) => !item.isPending && item.isCorrect === true).length
  return Math.round((correct / completed) * 100)
})

const selectedAnswerList = computed({
  get: () => {
    if (!currentQuestion.value || currentQuestion.value.type !== 'multi') return []
    return selectedAnswer.value ? selectedAnswer.value.split('').filter(Boolean) : []
  },
  set: (val) => {
    selectedAnswer.value = Array.isArray(val) ? val.sort().join('') : ''
  }
})

const loadAiExplanation = async () => {
  if (!currentQuestion.value) return
  aiLoading.value = true
  aiExplanation.value = ''
  try {
    const result = await getAiExplanation(currentQuestion.value.id)
    if (result.success) {
      aiExplanation.value = result.explanation
    } else {
      ElMessage.error(result.message || '获取讲解失败')
    }
  } catch (error) {
    ElMessage.error(`AI讲解失败：${error.response?.data?.detail || error.message}`)
  } finally {
    aiLoading.value = false
  }
}

const loadSubjects = async () => {
  try {
    loading.value = true
    subjects.value = await getSubjects()
  } catch (error) {
    ElMessage.error(`加载科目失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const handleSubjectClick = async (subject) => {
  // 点击科目卡片时，初始化该科目的复习设置（如果尚未初始化）
  if (!reviewModes.value[subject.id]) {
    reviewModes.value[subject.id] = 'sequential'
  }
  if (!reviewQuestionCounts.value[subject.id]) {
    reviewQuestionCounts.value[subject.id] = Math.min(10, subject.wrong_count || 10)
  }
  if (!reviewEndIndices.value[subject.id]) {
    reviewEndIndices.value[subject.id] = Math.min(10, subject.wrong_count || 10)
  }
}

const startReview = async (subject) => {
  if (!subject.wrong_count) {
    ElMessage.warning('该科目暂无错题')
    return
  }
  
  try {
    loading.value = true
    selectedSubject.value = subject
    
    // 获取当前科目的复习设置
    const mode = reviewModes.value[subject.id] || 'sequential'
    const questionCount = reviewQuestionCounts.value[subject.id] || Math.min(10, subject.wrong_count)
    const startIndex = reviewStartIndices.value[subject.id] || 1
    const endIndex = reviewEndIndices.value[subject.id] || Math.min(10, subject.wrong_count)
    
    // 加载所有错题
    const allWrongQuestions = await getWrongQuestions(subject.id)
    
    if (!allWrongQuestions.length) {
      ElMessage.warning('该科目暂无错题')
      selectedSubject.value = null
      return
    }
    
    // 根据复习方式选择题目
    let sessionQuestions = []
    if (mode === 'random') {
      // 随机抽题
      const count = Math.min(questionCount, allWrongQuestions.length)
      const shuffled = [...allWrongQuestions].sort(() => Math.random() - 0.5)
      sessionQuestions = shuffled.slice(0, count)
    } else if (mode === 'range') {
      // 范围复习
      const start = Math.max(1, startIndex) - 1
      const end = Math.min(endIndex, allWrongQuestions.length)
      sessionQuestions = allWrongQuestions.slice(start, end)
    } else {
      // 顺序复习
      const count = Math.min(questionCount, allWrongQuestions.length)
      sessionQuestions = allWrongQuestions.slice(0, count)
    }
    
    questions.value = sessionQuestions
    currentIndex.value = 0
    selectedAnswer.value = ''
    answers.value = {}
    showResult.value = false
    showExplanation.value = false
    currentResult.value = null
    pendingSubmissions.value = []
    
    ElMessage.success(`已加载 ${sessionQuestions.length} 道错题`)
  } catch (error) {
    ElMessage.error(`加载错题失败：${error.response?.data?.detail || error.message}`)
    selectedSubject.value = null
  } finally {
    loading.value = false
  }
}

const selectQuestion = (index) => {
  currentIndex.value = index
  selectedAnswer.value = ''
  aiExplanation.value = ''  // 切换题目时清空 AI 讲解
  const answerState = answers.value[index]
  if (answerState) {
    showResult.value = true
    showExplanation.value = true
    currentResult.value = answerState
    if (currentQuestion.value?.type === 'multi') {
      selectedAnswer.value = answerState.userAnswer
    } else {
      selectedAnswer.value = answerState.userAnswer
    }
  } else {
    showResult.value = false
    showExplanation.value = false
    currentResult.value = null
  }
}

const submitCurrentAnswer = async () => {
  if (!selectedAnswer.value || !currentQuestion.value) return
  
  const isFillQuestion = currentQuestion.value.type === 'fill'
  const isOptionQuestion = ['single', 'multi', 'judge'].includes(currentQuestion.value.type)

  // 立即判断选择题的对错
  if (isOptionQuestion) {
    let isCorrect = false
    let userAnswer = selectedAnswer.value
    
    if (currentQuestion.value.type === 'multi') {
      // 多选题：比较用户选择的所有选项
      const correctAnswers = currentQuestion.value.answer.split('').sort()
      const userAnswers = selectedAnswerList.value.sort()
      isCorrect = correctAnswers.join('') === userAnswers.join('')
      userAnswer = userAnswers.join('')
    } else {
      // 单选题和判断题
      isCorrect = selectedAnswer.value === currentQuestion.value.answer
    }
    
    answers.value[currentIndex.value] = {
      isCorrect: isCorrect,
      isPending: false,
      userAnswer: userAnswer
    }
    showResult.value = true
    showExplanation.value = true
    currentResult.value = answers.value[currentIndex.value]
    
    // 将答案加入待提交队列
    const existingSubmission = pendingSubmissions.value.find(s => s.question_id === currentQuestion.value.id)
    if (!existingSubmission) {
      pendingSubmissions.value.push({
        question_id: currentQuestion.value.id,
        user_answer: userAnswer,
        index: currentIndex.value
      })
    } else {
      existingSubmission.user_answer = userAnswer
    }
    
    if (isCorrect) {
      ElMessage.success('回答正确！')
    } else {
      ElMessage.error('回答错误，请查看正确答案')
    }
    
    if (currentIndex.value < questions.value.length - 1) {
      setTimeout(() => selectQuestion(currentIndex.value + 1), 1500)
    }
  } else if (isFillQuestion) {
    // 填空题：用户自判，不加入批量提交队列
    answers.value[currentIndex.value] = {
      isCorrect: null,
      isPending: true,
      userAnswer: selectedAnswer.value
    }
    showResult.value = true
    showExplanation.value = true
    ElMessage.info('已显示参考答案，请自行判断是否答对')
  } else {
    // 简答题和编程题：用户自判
    answers.value[currentIndex.value] = {
      isCorrect: null,
      isPending: true,
      userAnswer: selectedAnswer.value
    }
    showResult.value = true
    showExplanation.value = true
    
    const existingSubmission = pendingSubmissions.value.find(s => s.question_id === currentQuestion.value.id)
    if (!existingSubmission) {
      pendingSubmissions.value.push({
        question_id: currentQuestion.value.id,
        user_answer: selectedAnswer.value,
        index: currentIndex.value
      })
    } else {
      existingSubmission.user_answer = selectedAnswer.value
    }
    ElMessage.info('已显示参考答案，可自行判断或批量提交')
    if (currentIndex.value < questions.value.length - 1) {
      selectQuestion(currentIndex.value + 1)
    }
  }
}

const submitAllPending = async () => {
  if (pendingSubmissions.value.length === 0) {
    ElMessage.info('没有待提交的答案')
    return
  }
  
  batchSubmitting.value = true
  
  try {
    // 只传递question_id和user_answer，不传递额外的index字段
    const submissions = pendingSubmissions.value.map(s => ({
      question_id: s.question_id,
      user_answer: s.user_answer
    }))
    
    const result = await batchSubmitReviewAnswers(submissions)
    
    result.results.forEach(res => {
      if (res.error) {
        ElMessage.error(`第 ${res.question_id} 题提交失败: ${res.error}`)
        return
      }
      
      const submission = pendingSubmissions.value.find(s => s.question_id === res.question_id)
      if (submission) {
        // 对于选择题，使用前端已判断的结果
        const existingAnswer = answers.value[submission.index]
        if (existingAnswer && existingAnswer.isPending === false) {
          // 已经在前端判断过的选择题，保持前端判断结果
          answers.value[submission.index] = {
            isCorrect: existingAnswer.isCorrect,
            isPending: false,
            userAnswer: submission.user_answer
          }
        } else {
          // 其他题目（填空题、简答题等），使用后端返回的结果
          answers.value[submission.index] = {
            isCorrect: res.is_correct,
            isPending: false,
            userAnswer: submission.user_answer
          }
        }
      }
      
      if (res.is_correct) {
        if (res.removed_from_wrong) {
          ElMessage.success(`题目 ${res.question_id} 回答正确，已从错题本移除`)
        } else if (res.remaining_to_remove > 0) {
          ElMessage.success(`题目 ${res.question_id} 回答正确，还需再答对 ${res.remaining_to_remove} 次才会移出错题本`)
        }
      }
    })
    
    pendingSubmissions.value = []
    ElMessage.success(`批量提交完成，共提交 ${result.results.length} 题`)
  } catch (error) {
    console.error('批量提交失败:', error)
    ElMessage.error(`批量提交失败：${error.response?.data?.detail || error.message}`)
  } finally {
    batchSubmitting.value = false
  }
}

const submitSelfEvaluation = async (isCorrect) => {
  if (!currentQuestion.value || !currentAnswerState.value?.isPending) return
  loading.value = true
  try {
    const result = await submitReviewAnswer(currentQuestion.value.id, currentAnswerState.value.userAnswer)
    answers.value[currentIndex.value] = {
      isCorrect: isCorrect,
      isPending: false,
      userAnswer: currentAnswerState.value.userAnswer
    }
    
    pendingSubmissions.value = pendingSubmissions.value.filter(
      s => s.question_id !== currentQuestion.value.id
    )
    
    showResult.value = true
    showExplanation.value = true
    currentResult.value = answers.value[currentIndex.value]
    
    if (isCorrect) {
      if (result.removed_from_wrong) {
        ElMessage.success('回答正确，已从错题本移除')
      } else if (result.remaining_to_remove > 0) {
        ElMessage.success(`回答正确，还需再答对 ${result.remaining_to_remove} 次才会移出错题本`)
      } else {
        ElMessage.success('已标记为正确')
      }
      if (currentIndex.value < questions.value.length - 1) {
        selectQuestion(currentIndex.value + 1)
      }
    } else {
      ElMessage.warning('已标记为错误，并加入错题本')
    }
  } catch (error) {
    ElMessage.error(`提交自评失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const backToSubjects = () => {
  selectedSubject.value = null
  questions.value = []
  currentIndex.value = 0
  selectedAnswer.value = ''
  answers.value = {}
  showResult.value = false
  showExplanation.value = false
  currentResult.value = null
  pendingSubmissions.value = []
}

const resetReview = async () => {
  if (!selectedSubject.value) return
  await handleSubjectClick(selectedSubject.value)
}

const getQuestionTypeName = (type) => {
  const typeMap = {
    single: '单选',
    multi: '多选',
    judge: '判断',
    fill: '填空',
    short: '简答',
    code: '编程'
  }
  return typeMap[type] || type
}

const getSubjectIcon = (subjectName) => {
  const iconMap = {
    '大学英语': Document,
    'Web开发技术': Star,
    '数据结构': Refresh,
    '操作系统': Setting,
    '计算机网络': CircleClose,
    '数据库原理': List
  }
  return iconMap[subjectName] || Document
}

const handleKeyDown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    
    if (!hasAnswered.value && selectedAnswer.value && currentQuestion.value) {
      submitCurrentAnswer()
    } else if (hasAnswered.value && showSelfEvaluationActions.value) {
      // 如果是填空题自判阶段，不自动提交，让用户手动点击
      return
    }
  }
}

onMounted(async () => {
  await loadUserInfo()
  loadSubjects()
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
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
  transition: transform 0.3s ease;
}

.sidebar.collapsed {
  transform: translateX(-240px);
}

.sidebar.open {
  transform: translateX(0);
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 32px;
  color: #3b82f6;
}

.logo-copy h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.logo-copy span {
  font-size: 11px;
  color: #94a3b8;
  display: block;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-section-title {
  font-size: 11px;
  color: #64748b;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
  padding: 0 16px;
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
  color: white;
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
  transition: margin-left 0.3s ease;
}

.app-layout.sidebar-collapsed .main-content {
  margin-left: 0;
}

.desktop-sidebar-handle {
  position: fixed;
  left: 240px;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 60px;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 99;
  transition: left 0.3s ease;
  font-weight: bold;
  font-size: 14px;
}

.app-layout.sidebar-collapsed .desktop-sidebar-handle {
  left: 0;
}

.practice-page {
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  position: sticky;
  top: 0;
  z-index: 50;
}

.header-main {
  flex: 1;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.subject-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  color: #1e40af;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
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
  gap: 12px;
}

.subject-page {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}

.loading-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 48px;
  color: #909399;
  font-size: 14px;
}

.loading-wrapper .el-icon {
  font-size: 24px;
}

.subject-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.subject-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.subject-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.1);
  border-color: #3b82f6;
}

.subject-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1e40af;
  font-size: 24px;
}

.subject-info h3 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #303133;
}

.subject-info p {
  margin: 0 0 12px;
  color: #909399;
  font-size: 13px;
}

.review-mode-selection {
  margin: 12px 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.review-mode-selection .el-radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.range-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.range-controls span {
  color: #606266;
  font-size: 14px;
}

.range-controls .el-input-number {
  width: 80px;
}

.practice-main {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 24px;
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.practice-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 120px;
  height: fit-content;
  max-height: calc(100vh - 120px);
}

.sidebar-stats {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.stat-item {
  text-align: center;
  padding: 8px;
  background: #f5f7fa;
  border-radius: 6px;
}

.stat-label {
  display: block;
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.question-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.question-dot {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 500;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s ease;
}

.question-dot:hover {
  border-color: #3b82f6;
  color: #3b82f6;
}

.question-dot.active {
  border-color: #3b82f6;
  background: #3b82f6;
  color: white;
}

.question-dot.answered {
  background: #f0f9eb;
  border-color: #c2e7b0;
  color: #67c23a;
}

.question-dot.pending {
  background: #fff7e6;
  border-color: #ffd591;
  color: #faad14;
}

.question-dot.correct {
  background: #f0f9eb;
  border-color: #c2e7b0;
  color: #67c23a;
}

.question-dot.wrong {
  background: #fef0f0;
  border-color: #fbc4c4;
  color: #f56c6c;
}

.batch-submit-btn {
  width: 100%;
}

.question-content {
  min-height: 0;
}

.question-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.question-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.question-number {
  font-size: 14px;
  font-weight: 500;
  color: #909399;
}

.question-type-badge {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.question-type-badge.type-single {
  background: #dbeafe;
  color: #1e40af;
}

.question-type-badge.type-multi {
  background: #fce7f3;
  color: #9d174d;
}

.question-type-badge.type-judge {
  background: #fef3c7;
  color: #92400e;
}

.question-type-badge.type-fill {
  background: #e0f2fe;
  color: #075985;
}

.question-type-badge.type-short {
  background: #dcfce7;
  color: #166534;
}

.question-type-badge.type-code {
  background: #f3e8ff;
  color: #6b21a8;
}

.question-text {
  font-size: 18px;
  line-height: 1.7;
  color: #303133;
  margin-bottom: 24px;
  white-space: pre-wrap;
}

.options {
  display: grid;
  gap: 12px;
  margin-bottom: 24px;
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

.option-item.selected {
  border-color: #3b82f6;
  background: #f0f9ff;
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
  color: #606266;
}

.answer-input-wrap {
  margin-bottom: 24px;
}

.result-box {
  padding: 16px;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
}

.result-box.correct {
  background: #f0f9eb;
  border: 1px solid #c2e7b0;
  color: #67c23a;
}

.result-box.wrong {
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  color: #f56c6c;
}

.result-box.pending {
  background: #fff7e6;
  border: 1px solid #ffd591;
  color: #faad14;
}

.result-icon {
  font-size: 24px;
}

.result-content h3 {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
}

.result-content p {
  margin: 0;
  font-size: 13px;
  opacity: 0.8;
}

.self-evaluation-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.self-evaluation-actions .el-button {
  flex: 1;
}

.action-buttons {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-240px);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .main-content {
    margin-left: 0;
  }

  .desktop-sidebar-handle {
    display: none;
  }

  .practice-main {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .practice-sidebar {
    position: relative;
    top: 0;
    max-height: none;
  }

  .subject-grid {
    grid-template-columns: 1fr;
  }
}

/* AI 讲解样式 */
.explanation-box.ai {
  margin-top: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border: 1px solid #93c5fd;
  border-radius: 8px;
}

.explanation-box.ai h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #1d4ed8;
  display: flex;
  align-items: center;
  gap: 8px;
}

.explanation-box.ai h3::before {
  content: '🤖';
}

.explanation-content {
  font-size: 14px;
  line-height: 1.8;
  color: #334155;
}

.explanation-content :deep(h2) {
  font-size: 15px;
  color: #2563eb;
  margin: 12px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #bfdbfe;
}

.explanation-content :deep(h3) {
  font-size: 14px;
  color: #3b82f6;
  margin: 10px 0 4px;
}

.explanation-content :deep(strong) {
  color: #dc2626;
}
</style>