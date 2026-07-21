<template>
  <Layout :username="username" :avatar="avatar" @show-profile="showProfileModal = true" @logout="handleLogout">
    <div class="practice-page">
        <header class="page-header">
          <div class="header-main">
            <div class="header-nav">
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
                <p>{{ getReviewSourceCountLabel(subject) }}</p>
                <div class="review-mode-selection">
                  <el-radio-group
                    :model-value="reviewSources[subject.id] || 'wrong'"
                    @update:model-value="(source) => updateReviewSource(subject.id, source)"
                    size="small"
                  >
                    <el-radio-button label="wrong">复习错题</el-radio-button>
                    <el-radio-button label="important">复习重点题</el-radio-button>
                    <el-radio-button label="combined">错题和重点题总和</el-radio-button>
                  </el-radio-group>
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
                        :max="Math.max(subject.question_count || 1, 1)"
                        :step="1"
                        controls-position="right"
                        size="small"
                      />
                      <span>-</span>
                      <el-input-number
                        :model-value="reviewEndIndices[subject.id] || Math.min(10, subject.wrong_count)"
                        @update:model-value="(val) => reviewEndIndices[subject.id] = val"
                        :min="(reviewStartIndices[subject.id] || 1)"
                        :max="Math.max(subject.question_count || 1, 1)"
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
                      :max="Math.max(subject.question_count || 1, 1)"
                      :step="1"
                      controls-position="right"
                      size="small"
                    />
                  </template>
                </div>
                <el-button type="primary" @click="startReview(subject)">开始复习</el-button>
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
                :key="q.question_id || q.id"
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
                  <p v-if="currentQuestion.answer">参考答案：{{ displayAnswer(currentQuestion) }}</p>
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
                <el-button v-if="showResult && !currentQuestion?.explanation" :icon="ChatDotRound" :loading="aiLoading" @click="loadAiExplanation">
                  AI讲解
                </el-button>
                <el-button v-else-if="currentQuestion?.explanation" type="info" disabled>
                  已有解析
                </el-button>
              </div>

              <!-- 解析内容 -->
              <div v-if="showResult && currentQuestion?.explanation" class="explanation-box">
                <div class="explanation-header">
                  <h3>题目解析</h3>
                  <div class="explanation-actions">
                    <el-button v-if="!editingExplanation" size="small" text @click="startEditExplanation">
                      编辑
                    </el-button>
                    <template v-else>
                      <el-button size="small" type="primary" @click="saveExplanation">
                        保存
                      </el-button>
                      <el-button size="small" text @click="cancelEditExplanation">
                        取消
                      </el-button>
                    </template>
                  </div>
                </div>
                <div v-if="!editingExplanation" class="explanation-content" v-html="renderedQuestionExplanation"></div>
                <textarea v-else v-model="editableExplanation" class="explanation-textarea"></textarea>
              </div>
            </div>
          </div>
        </main>
      </div>

      <ProfileModal
        v-model:visible="showProfileModal"
        :username="username"
      />
</Layout>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import ProfileModal from '../components/ProfileModal.vue'
import Layout from '../components/Layout/Layout.vue'
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
import { useUser } from '../composables/useUser'
import { getSubjects, getWrongQuestions, getQuestions, submitReviewAnswer, batchSubmitReviewAnswers, getAiExplanation, updateQuestionExplanation } from '../api'
import { getErrorMessage } from '../utils/errorHandler'
import { clearAuthSession } from '../utils/authStorage'

const router = useRouter()
const route = useRoute()
const { username, avatar, loadUserInfo } = useUser()

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
const editingExplanation = ref(false)
const editableExplanation = ref('')

const reviewModes = ref({})
const reviewSources = ref({})
const reviewQuestionCounts = ref({})
const reviewStartIndices = ref({})
const reviewEndIndices = ref({})
const importantCounts = ref({})
const combinedCounts = ref({})

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

const updateReviewSource = (subjectId, source) => {
  reviewSources.value[subjectId] = source
}

const getReviewSourceCount = (subject) => {
  const source = reviewSources.value[subject.id] || 'wrong'
  const wrongCount = subject.wrong_count || 0
  const importantCount = importantCounts.value[subject.id] || 0

  if (source === 'important') return importantCount
  if (source === 'combined') return combinedCounts.value[subject.id] || 0
  return wrongCount
}

const getReviewSourceCountLabel = (subject) => {
  const source = reviewSources.value[subject.id] || 'wrong'
  const count = getReviewSourceCount(subject)

  if (source === 'important') return `${count} 道重点题`
  if (source === 'combined') return `${count} 道错题和重点题总和`
  return `${count} 道错题`
}



const handleLogout = () => {
  clearAuthSession()
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const currentQuestion = computed(() => questions.value[currentIndex.value])
const currentQuestionId = computed(() => currentQuestion.value?.question_id ?? currentQuestion.value?.id ?? null)
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

const renderedExplanation = computed(() => {
  if (!aiExplanation.value) return ''
  let html = aiExplanation.value
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  return html
})

const renderedQuestionExplanation = computed(() => {
  if (!currentQuestion.value?.explanation) return ''
  let html = currentQuestion.value.explanation
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
  if (!currentQuestion.value || !currentQuestionId.value) {
    ElMessage.error('当前题目缺少有效ID，无法获取AI讲解')
    return
  }
  aiLoading.value = true
  aiExplanation.value = ''
  try {
    const result = await getAiExplanation(currentQuestionId.value)
    if (result.success) {
      const saveResult = await updateQuestionExplanation(currentQuestionId.value, result.explanation)
      if (saveResult.success) {
        currentQuestion.value.explanation = result.explanation
        editingExplanation.value = false
        editableExplanation.value = ''
        ElMessage.success('AI解析已自动保存')
      } else {
        ElMessage.error('AI解析生成成功，但自动保存失败')
      }
    } else {
      ElMessage.error(result.message || '获取讲解失败')
    }
  } catch (error) {
    ElMessage.error(`AI讲解失败：${getErrorMessage(error, '获取讲解失败')}`)
  } finally {
    aiLoading.value = false
  }
}

const startEditExplanation = () => {
  editableExplanation.value = currentQuestion.value?.explanation || ''
  editingExplanation.value = true
}

const cancelEditExplanation = () => {
  editingExplanation.value = false
  editableExplanation.value = ''
}

const saveExplanation = async () => {
  if (!currentQuestion.value || !currentQuestionId.value) {
    ElMessage.error('当前题目缺少有效ID，无法保存解析')
    return
  }
  try {
    const result = await updateQuestionExplanation(currentQuestionId.value, editableExplanation.value)
    if (result.success) {
      currentQuestion.value.explanation = editableExplanation.value
      editingExplanation.value = false
      editableExplanation.value = ''
      ElMessage.success('解析保存成功')
    } else {
      ElMessage.error('保存失败')
    }
  } catch (error) {
    ElMessage.error(`保存失败：${getErrorMessage(error, '保存失败')}`)
  }
}

const loadSubjects = async () => {
  try {
    loading.value = true
    subjects.value = await getSubjects()
    const [allWrongQuestions, allImportantQuestions] = await Promise.all([
      getWrongQuestions(),
      getQuestions(0, 1000, null, 'all', true)
    ])

    const wrongIdsBySubject = new Map()
    allWrongQuestions.forEach((question) => {
      const subjectId = question.subject_id
      if (!subjectId) return
      if (!wrongIdsBySubject.has(subjectId)) wrongIdsBySubject.set(subjectId, new Set())
      wrongIdsBySubject.get(subjectId).add(question.question_id || question.id)
    })

    const importantCountMap = {}
    const combinedCountMap = {}

    allImportantQuestions.forEach((question) => {
      const subjectId = question.subject_id
      if (!subjectId) return
      importantCountMap[subjectId] = (importantCountMap[subjectId] || 0) + 1
    })

    subjects.value.forEach((subject) => {
      const subjectId = subject.id
      const wrongIds = wrongIdsBySubject.get(subjectId) || new Set()
      const importantQuestions = allImportantQuestions.filter((question) => question.subject_id === subjectId)
      const importantOnlyCount = importantQuestions.filter((question) => !wrongIds.has(question.id)).length

      importantCountMap[subjectId] = importantCountMap[subjectId] || 0
      combinedCountMap[subjectId] = wrongIds.size + importantOnlyCount
    })

    importantCounts.value = importantCountMap
    combinedCounts.value = combinedCountMap
  } catch (error) {
    ElMessage.error(`加载科目失败：${getErrorMessage(error, '加载失败')}`)
  } finally {
    loading.value = false
  }
}

const handleSubjectClick = async (subject) => {
  // 点击科目卡片时，初始化该科目的复习设置（如果尚未初始化）
  if (!reviewSources.value[subject.id]) {
    reviewSources.value[subject.id] = 'wrong'
  }
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
  try {
    loading.value = true
    selectedSubject.value = subject
    
    // 获取当前科目的复习设置
    const source = reviewSources.value[subject.id] || 'wrong'
    const mode = reviewModes.value[subject.id] || 'sequential'
    const questionCount = reviewQuestionCounts.value[subject.id] || Math.min(10, subject.question_count || 10)
    const startIndex = reviewStartIndices.value[subject.id] || 1
    const endIndex = reviewEndIndices.value[subject.id] || Math.min(10, subject.question_count || 10)

    const [allWrongQuestions, allImportantQuestions] = await Promise.all([
      getWrongQuestions(subject.id),
      getQuestions(0, 1000, subject.id, 'all', true)
    ])

    const wrongQuestionIds = new Set(allWrongQuestions.map((question) => question.question_id || question.id))
    let sourceQuestions = []

    if (source === 'wrong') {
      sourceQuestions = allWrongQuestions
    } else if (source === 'important') {
      sourceQuestions = allImportantQuestions.map((question) => ({
        question_id: question.id,
        subject_id: question.subject_id,
        type: question.type,
        content: question.content,
        options: question.options,
        answer: question.answer,
        explanation: question.explanation,
        is_important: question.is_important,
      }))
    } else {
      const importantOnlyQuestions = allImportantQuestions
        .filter((question) => !wrongQuestionIds.has(question.id))
        .map((question) => ({
          question_id: question.id,
          subject_id: question.subject_id,
          type: question.type,
          content: question.content,
          options: question.options,
          answer: question.answer,
          explanation: question.explanation,
          is_important: question.is_important,
        }))

      sourceQuestions = [...allWrongQuestions, ...importantOnlyQuestions]
    }

    if (!sourceQuestions.length) {
      const sourceLabel = source === 'important' ? '重点题' : source === 'combined' ? '错题和重点题总和' : '错题'
      ElMessage.warning(`该科目暂无可复习的${sourceLabel}`)
      selectedSubject.value = null
      return
    }
    
    // 根据复习方式选择题目
    let sessionQuestions = []
    if (mode === 'random') {
      const count = Math.min(questionCount, sourceQuestions.length)
      const shuffled = [...sourceQuestions].sort(() => Math.random() - 0.5)
      sessionQuestions = shuffled.slice(0, count)
    } else if (mode === 'range') {
      const start = Math.max(1, startIndex) - 1
      const end = Math.min(endIndex, sourceQuestions.length)
      sessionQuestions = sourceQuestions.slice(start, end)
    } else {
      const count = Math.min(questionCount, sourceQuestions.length)
      sessionQuestions = sourceQuestions.slice(0, count)
    }
    
    questions.value = sessionQuestions
    currentIndex.value = 0
    selectedAnswer.value = ''
    answers.value = {}
    showResult.value = false
    showExplanation.value = false
    currentResult.value = null
    pendingSubmissions.value = []
    
    const sourceLabel = source === 'important' ? '重点题' : source === 'combined' ? '错题和重点题总和' : '错题'
    ElMessage.success(`已加载 ${sessionQuestions.length} 道${sourceLabel}`)
  } catch (error) {
    ElMessage.error(`加载错题失败：${getErrorMessage(error, '加载失败')}`)
    selectedSubject.value = null
  } finally {
    loading.value = false
  }
}

const selectQuestion = (index) => {
  currentIndex.value = index
  selectedAnswer.value = ''
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
    const existingSubmission = pendingSubmissions.value.find(s => s.question_id === currentQuestionId.value)
    if (!existingSubmission) {
      pendingSubmissions.value.push({
        question_id: currentQuestionId.value,
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
    
    const existingSubmission = pendingSubmissions.value.find(s => s.question_id === currentQuestionId.value)
    if (!existingSubmission) {
      pendingSubmissions.value.push({
        question_id: currentQuestionId.value,
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
    ElMessage.error(`批量提交失败：${getErrorMessage(error, '提交失败')}`)
  } finally {
    batchSubmitting.value = false
  }
}

const submitSelfEvaluation = async (isCorrect) => {
  if (!currentQuestion.value || !currentAnswerState.value?.isPending) return
  loading.value = true
  try {
    const result = await submitReviewAnswer(currentQuestionId.value, currentAnswerState.value.userAnswer)
    answers.value[currentIndex.value] = {
      isCorrect: isCorrect,
      isPending: false,
      userAnswer: currentAnswerState.value.userAnswer
    }
    
    pendingSubmissions.value = pendingSubmissions.value.filter(
      s => s.question_id !== currentQuestionId.value
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
    ElMessage.error(`提交自评失败：${getErrorMessage(error, '提交失败')}`)
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

const displayAnswer = (question) => {
  if (!question) return ''
  if (question.type === 'judge') {
    return question.answer === 'T' ? '正确' : question.answer === 'F' ? '错误' : question.answer
  }
  return question.answer || ''
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
  --sidebar-width: clamp(220px, 18vw, 256px);
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, rgba(184, 92, 56, 0.08) 0%, rgba(184, 92, 56, 0.04) 50%, rgba(139, 63, 31, 0.06) 100%);
}

.sidebar {
  width: var(--sidebar-width);
  background: linear-gradient(180deg, #3d2f24 0%, #2c2416 100%);
  color: #f8f4ec;
  display: flex;
  flex-direction: column;
  position: relative;
  flex: 0 0 var(--sidebar-width);
  min-height: 100vh;
  z-index: 100;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 0;
  flex-basis: 0;
  opacity: 0;
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
  color: #b85c38;
}

.logo-copy h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

.logo-copy span {
  font-size: 11px;
  color: #a89985;
  display: block;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.nav-section-title {
  font-size: 11px;
  color: #8b7b65;
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
  color: #a89985;
}

.nav-item:hover {
  background: rgba(184, 92, 56, 0.1);
  color: #f8f4ec;
}

.nav-item.active {
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
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
  padding: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(184, 92, 56, 0.05);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 20px rgba(44, 36, 22, 0.1);
  transition: box-shadow 0.25s ease, transform 0.25s ease;
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.12);
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
  box-shadow: 0 4px 12px rgba(184, 92, 56, 0.3);
  cursor: pointer;
  flex-shrink: 0;
}

.user-details {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.username {
  font-weight: 600;
  font-size: 15px;
  color: #f8f4ec;
}

.logout-btn {
  font-size: 13px;
  color: #a89985;
  cursor: pointer;
  transition: color 0.2s ease, background 0.2s ease;
  border-radius: 8px;
  padding: 4px 8px;
  width: fit-content;
}

.logout-btn:hover {
  color: #e8dfd0;
  background: rgba(166, 52, 52, 0.2);
}

.main-content {
  flex: 1;
  position: relative;
  min-width: 0;
  min-height: 100vh;
  transition: width 0.25s ease;
}

.desktop-sidebar-handle {
  position: fixed;
  top: 24px;
  left: calc(var(--sidebar-width, 240px) - 18px);
  z-index: 110;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(184, 92, 56, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #b85c38;
  font-size: 18px;
  line-height: 1;
  box-shadow: 0 10px 24px rgba(44, 36, 22, 0.12);
  cursor: pointer;
  transition: left 0.25s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.desktop-sidebar-handle:hover {
  background: #b85c38;
  color: #fff;
  box-shadow: 0 14px 28px rgba(184, 92, 56, 0.3);
}

.desktop-sidebar-handle.collapsed {
  left: 12px;
}

.practice-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: clamp(16px, 2vw, 24px);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid #dbe3ef;
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
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
  gap: 8px;
  min-width: 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(184, 92, 56, 0.1);
  color: #b85c38;
  font-size: 13px;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #303133;
}

.page-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.header-actions,
.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.subject-page {
  width: 100%;
  margin: 0 auto;
  padding: clamp(16px, 2vw, 24px);
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
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: 18px;
}

.subject-card {
  min-height: 220px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(248, 244, 236, 0.94) 100%);
  border: 1px solid #e8dfd0;
  border-radius: 18px;
  padding: 22px;
  cursor: pointer;
  transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(44, 36, 22, 0.05);
}

.subject-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #b85c38 0%, #8d3f1f 52%, #5c8a35 100%);
}

.subject-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 18px 40px rgba(44, 36, 22, 0.12);
  border-color: #b85c38;
}

.subject-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(184, 92, 56, 0.15) 0%, rgba(184, 92, 56, 0.08) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b85c38;
  font-size: 28px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.subject-info h3 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #303133;
}

.subject-info p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.review-mode-selection {
  margin: 2px 0 6px;
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  flex: 1;
  display: grid;
  grid-template-columns: clamp(240px, 22vw, 320px) minmax(0, 1fr);
  gap: clamp(14px, 1.8vw, 24px);
  padding: clamp(16px, 2vw, 24px);
  align-items: start;
}

.practice-sidebar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 24px;
  align-self: start;
}

.sidebar-stats {
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid #e8dfd0;
  border-radius: 18px;
  padding: 16px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  box-shadow: 0 10px 28px rgba(44, 36, 22, 0.08);
}

.stat-item {
  text-align: center;
  padding: 10px 8px;
  background: linear-gradient(180deg, #f8f4ec 0%, #e8dfd0 100%);
  border-radius: 12px;
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
  gap: 8px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(12px);
  border: 1px solid #dbe3ef;
  border-radius: 18px;
  padding: 14px;
  max-height: calc(100vh - 280px);
  overflow-y: auto;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
}

.question-dot {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid #d7deea;
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
  border-color: #b85c38;
  color: #b85c38;
}

.question-dot.active {
  border-color: #b85c38;
  background: #b85c38;
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
  min-width: 0;
  display: flex;
}

.question-card {
  width: 100%;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(12px);
  border: 1px solid #e8dfd0;
  border-radius: 22px;
  padding: clamp(20px, 2vw, 28px);
  box-shadow: 0 16px 40px rgba(44, 36, 22, 0.08);
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
  background: rgba(184, 92, 56, 0.12);
  color: #8d3f1f;
}

.question-type-badge.type-multi {
  background: rgba(166, 52, 52, 0.12);
  color: #8b2a2a;
}

.question-type-badge.type-judge {
  background: rgba(184, 134, 11, 0.12);
  color: #8b6914;
}

.question-type-badge.type-fill {
  background: rgba(61, 122, 138, 0.12);
  color: #2a5a68;
}

.question-type-badge.type-short {
  background: rgba(92, 138, 53, 0.12);
  color: #3d5f24;
}

.question-type-badge.type-code {
  background: rgba(139, 63, 31, 0.12);
  color: #6b3f1f;
}

.question-text {
  padding: 18px;
  background: linear-gradient(180deg, #f8f4ec 0%, #f0ebe0 100%);
  border-radius: 14px;
  font-size: 18px;
  line-height: 1.8;
  color: #1f2937;
  margin-bottom: 24px;
  white-space: pre-wrap;
}

.options {
  display: grid;
  gap: 12px;
  margin-bottom: 24px;
}

.option-item {
  padding: 14px 16px;
  border: 1px solid #e8dfd0;
  border-radius: 14px;
  transition: all 0.2s ease;
  cursor: pointer;
  background: #fff;
}

.option-item:hover {
  border-color: #d4c8b4;
}

.option-item.selected {
  border-color: #b85c38;
  background: rgba(184, 92, 56, 0.08);
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

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    transform: translateX(-100%);
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

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-actions,
  .action-buttons {
    width: 100%;
  }

  .action-buttons {
    justify-content: stretch;
  }

  .action-buttons > * {
    flex: 1 1 auto;
  }
}

/* AI 讲解样式 */
.explanation-box.ai {
  display: none;
}

.explanation-box.ai h3 {
  display: none;
}

.explanation-box.ai h3::before {
  content: '';
}

.explanation-content {
  font-size: 14px;
  line-height: 1.8;
  color: #334155;
}

.explanation-content :deep(h2) {
  font-size: 15px;
  color: #8d3f1f;
  margin: 12px 0 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #e8dfd0;
}

.explanation-content :deep(h3) {
  font-size: 14px;
  color: #b85c38;
  margin: 10px 0 4px;
}

.explanation-content :deep(strong) {
  color: #a63434;
}

.explanation-box {
  margin-top: 20px;
  padding: 16px;
  background: linear-gradient(135deg, #f8f4ec 0%, #e8dfd0 100%);
  border: 1px solid #fbbf24;
  border-radius: 8px;
}

.explanation-box h3 {
  margin: 0 0 12px;
  font-size: 15px;
  color: #b45309;
  display: flex;
  align-items: center;
  gap: 8px;
}

.explanation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.explanation-actions {
  display: flex;
  gap: 8px;
}

.explanation-textarea {
  width: 100%;
  min-height: 150px;
  padding: 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 14px;
  line-height: 1.6;
  resize: vertical;
}
</style>
