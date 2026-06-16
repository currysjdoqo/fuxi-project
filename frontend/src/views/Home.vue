<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
    <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, open: mobileNavOpen }">
      <div class="logo-section">
        <div class="logo-group">
          <el-icon class="logo-icon"><Document /></el-icon>
          <div v-if="!sidebarCollapsed || isMobileNav" class="logo-copy">
            <h2>??????</h2>
            <span>Practice Workspace</span>
          </div>
        </div>
        <el-button
          v-if="!isMobileNav"
          circle
          text
          class="sidebar-toggle desktop-toggle"
          :icon="sidebarCollapsed ? Expand : Fold"
          @click="toggleSidebar"
        />
        <el-button
          v-else
          circle
          text
          class="sidebar-toggle mobile-close"
          :icon="Close"
          @click="closeMobileNav"
        />
      </div>

      <div class="nav-menu">
        <div class="nav-section-title" v-if="!sidebarCollapsed || isMobileNav">功能导航</div>
        <div
          v-for="item in navItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          @click="goToPath(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span v-if="!sidebarCollapsed || isMobileNav">{{ item.label }}</span>
        </div>
      </div>

      <div class="user-section">
        <div class="user-info">
          <div class="avatar">👤</div>
          <div v-if="!sidebarCollapsed || isMobileNav" class="user-details">
            <span class="username">{{ username }}</span>
            <span class="logout-btn" @click="handleLogout">退出登录</span>
          </div>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <div class="practice-page">
        <header class="page-header">
          <div class="header-main">
            <div class="header-nav">
              <el-button
                circle
                text
                class="header-nav-btn"
                :icon="isMobileNav ? Menu : (sidebarCollapsed ? Expand : Fold)"
                @click="isMobileNav ? toggleMobileNav() : toggleSidebar()"
              />
              <div v-if="selectedSubject" class="subject-chip">
                <el-icon><Document /></el-icon>
                <span>{{ selectedSubject.name }}</span>
              </div>
            </div>
            <h1>{{ selectedSubject ? `${selectedSubject.name} - 练习模式` : '选择科目' }}</h1>
            <p>{{ selectedSubject ? '逐题作答，也可以切换删题模式整理题库。' : '先创建或选择一个科目，然后开始练习。' }}</p>
          </div>
          <div class="header-actions">
            <el-button v-if="selectedSubject" :icon="Back" @click="backToSubjects">返回科目</el-button>
            <el-button
              v-if="selectedSubject && selectedSubject.name !== '未分类'"
              type="danger"
              plain
              :icon="Delete"
              :loading="subjectDeletingId === selectedSubject.id"
              @click="handleDeleteSubject(selectedSubject)"
            >
              删除练习集
            </el-button>
            <el-button v-if="selectedSubject" :icon="Refresh" @click="resetPractice">重新开始</el-button>
          </div>
        </header>

        <main v-if="!selectedSubject" class="subject-page">
          <transition name="plan-float">
            <aside 
              v-if="showPlanFloat" 
              class="plan-float" 
              :class="{ collapsed: planFloatCollapsed }"
              :style="planFloatStyle"
            >
              <div v-if="planFloatCollapsed" class="plan-float-collapsed-trigger" @click="togglePlanFloat">
                <el-icon><List /></el-icon>
                <span class="plan-float-collapsed-label">计划</span>
              </div>
              
              <div v-else class="plan-float-content">
                <div class="plan-float-header" @pointerdown="startPlanFloatDrag">
                  <div>
                    <p>今日学习计划</p>
                    <h3>{{ formatPlanDate(todayPlanDate) }}</h3>
                  </div>
                  <div class="plan-float-actions">
                    <el-button
                      link
                      :icon="planPanelCollapsed ? ArrowRight : ArrowLeft"
                      @pointerdown.stop
                      @click="planPanelCollapsed = !planPanelCollapsed"
                    />
                    <el-button
                      link
                      :icon="ArrowRight"
                      @pointerdown.stop
                      @click="togglePlanFloat"
                      title="收起"
                    />
                  </div>
                </div>

                <div v-if="!planPanelCollapsed" class="plan-float-body">
                  <el-skeleton v-if="planLoading" :rows="3" animated />
                  <template v-else>
                    <div v-if="todayPlanItems.length" class="plan-float-list">
                      <div
                        v-for="item in todayPlanItems"
                        :key="item.id"
                        class="plan-float-item"
                        :class="{ completed: item.completed === 1 }"
                        @click="completePlanItem(item)"
                      >
                        <el-icon class="plan-float-status">
                          <CircleCheck v-if="item.completed === 1" />
                          <CircleClose v-else />
                        </el-icon>
                        <span>{{ item.content }}</span>
                        <span class="plan-float-hint">点击完成</span>
                      </div>
                    </div>
                    <el-empty v-else description="今天还没有学习计划" :image-size="80" />
                  </template>
                </div>
              </div>
            </aside>
          </transition>

          <section class="create-subject">
            <el-input v-model="newSubjectName" placeholder="例如：机器学习" @keyup.enter="handleCreateSubject" />
            <el-button type="primary" :icon="Plus" :loading="subjectCreating" @click="handleCreateSubject">创建科目</el-button>
          </section>

          <section class="subject-grid">
            <div
              v-for="subject in subjects"
              :key="subject.id"
              class="subject-card"
              role="button"
              tabindex="0"
              @click="enterSubject(subject)"
              @keyup.enter="enterSubject(subject)"
              @keyup.space="enterSubject(subject)"
            >
              <div class="subject-card-head">
                <strong>{{ subject.name }}</strong>
                <el-button
                  v-if="subject.name !== '未分类'"
                  circle
                  size="small"
                  type="danger"
                  :icon="Delete"
                  :loading="subjectDeletingId === subject.id"
                  @click.stop="handleDeleteSubject(subject)"
                />
              </div>
              <span>{{ subject.question_count }} 道题</span>
            </div>
            <el-empty v-if="!subjects.length" description="暂无科目，请先创建一个科目" />
          </section>
        </main>

        <template v-else>
          <section class="type-filter">
            <div class="practice-toolbar">
              <el-segmented v-model="selectedQuestionType" :options="questionTypeOptions" @change="loadQuestions" />
              <div class="practice-mode-controls">
                <el-radio-group v-model="practiceMode" @change="applyPracticeQuestions()">
                  <el-radio-button label="sequential">顺序练习</el-radio-button>
                  <el-radio-button label="random">随机抽题</el-radio-button>
                </el-radio-group>
                <el-input-number
                  v-model="practiceQuestionCount"
                  :min="1"
                  :max="Math.max(allQuestions.length, 1)"
                  :step="1"
                  controls-position="right"
                  class="count-input"
                />
                <el-button :disabled="!allQuestions.length" @click="applyPracticeQuestions()">
                  {{ practiceMode === 'random' ? '重新抽题' : '应用数量' }}
                </el-button>
              </div>
            </div>
          </section>

          <main class="practice-layout">
            <aside ref="questionListRef" class="question-list">
              <div class="list-title">
                <span>题目列表</span>
                <el-switch
                  v-model="deleteMode"
                  inline-prompt
                  active-text="删"
                  inactive-text="练"
                />
              </div>
              <div v-if="deleteMode" class="batch-bar">
                <span>已选 {{ batchSelectedIds.length }}</span>
                <el-button size="small" @click="selectAllForBatch">全选</el-button>
                <el-button size="small" @click="batchSelectedIds = []">清空</el-button>
                <el-button size="small" type="danger" :disabled="!batchSelectedIds.length" :loading="batchDeleting" @click="batchDeleteSelected">
                  批量删除
                </el-button>
              </div>
              <button
                v-for="(q, index) in questions"
                :key="q.id"
                :data-index="index"
                class="question-item"
                :class="{ active: currentIndex === index, done: answers[index], deleting: deleteMode }"
                @click="selectQuestion(index)"
              >
                <span class="question-number">{{ index + 1 }}</span>
                <el-checkbox
                  v-if="deleteMode"
                  :model-value="batchSelectedIds.includes(q.id)"
                  @click.stop
                  @change="toggleBatchSelection(q.id)"
                />
                <span class="question-summary">{{ truncateContent(q.content) }}</span>
                <el-icon v-if="q.is_important" class="important-star"><StarFilled /></el-icon>
                <el-icon v-if="deleteMode" class="status wrong"><Delete /></el-icon>
                <el-icon v-else-if="answers[index]?.isPending" class="status pending"><Select /></el-icon>
                <el-icon v-else-if="answers[index]?.isCorrect" class="status correct"><CircleCheck /></el-icon>
                <el-icon v-else-if="answers[index]" class="status wrong"><CircleClose /></el-icon>
              </button>
            </aside>

            <section class="question-panel">
              <el-empty v-if="!currentQuestion" description="当前科目暂无题目，请先导入习题" />

              <div v-else class="question-card">
                <div class="question-meta">
                  <div class="type-editor">
                    <el-tag :type="deleteMode ? 'danger' : 'primary'">{{ deleteMode ? '删题模式' : questionTypeLabel(currentQuestion.type) }}</el-tag>
                    <el-select
                      v-model="currentQuestion.type"
                      size="small"
                      class="question-type-select"
                      :disabled="deleteMode || typeUpdating"
                      @change="updateCurrentQuestionType"
                    >
                      <el-option v-for="item in editableTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
                    </el-select>
                  </div>
                  <div class="meta-right">
                    <el-button
                      circle
                      :type="currentQuestion.is_important ? 'warning' : 'default'"
                      :icon="currentQuestion.is_important ? StarFilled : Star"
                      :loading="importantUpdating"
                      @click="toggleCurrentImportant"
                    />
                    <span>第 {{ currentIndex + 1 }} / {{ questions.length }} 题</span>
                  </div>
                </div>

                <div class="question-content">{{ currentQuestion.content }}</div>

                <div v-if="hasAttachmentAsset" class="attachment-panel">
                  <div class="attachment-header">
                    <div>
                      <strong>{{ attachmentName }}</strong>
                      <p>{{ isPreviewableAttachment ? '可在线预览，也可直接下载。' : '该附件不支持在线预览，请直接下载或新窗口打开。' }}</p>
                    </div>
                    <div class="attachment-actions">
                      <el-button v-if="attachmentSourceUrl" size="small" @click="openAttachment">
                        打开附件
                      </el-button>
                      <el-button v-if="attachmentDownloadUrl" size="small" type="primary" @click="downloadAttachment">
                        下载附件
                      </el-button>
                    </div>
                  </div>

                  <img
                    v-if="isImageAttachment"
                    :src="attachmentSourceUrl"
                    :alt="attachmentName"
                    class="attachment-image"
                  />
                  <iframe
                    v-else-if="isPdfAttachment"
                    :src="attachmentSourceUrl"
                    class="attachment-frame"
                    title="附件预览"
                  />
                </div>

                <el-radio-group
                  v-if="isOptionQuestion && !isMultiQuestion"
                  v-model="selectedAnswer"
                  class="options"
                  :disabled="hasAnswered || deleteMode"
                >
                  <label
                    v-for="item in answerOptions"
                    :key="item.key"
                    class="option-item"
                    :class="{
                      correct: showResult && item.key === currentQuestion.answer,
                      wrong: showResult && selectedAnswer === item.key && !answers[currentIndex]?.isCorrect
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
                  :disabled="hasAnswered || deleteMode"
                >
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

                <div v-else class="text-answer">
                  <el-input
                    v-model="selectedAnswer"
                    :type="['short', 'code'].includes(currentQuestion.type) ? 'textarea' : 'text'"
                    :rows="currentQuestion.type === 'code' ? 8 : currentQuestion.type === 'short' ? 5 : 1"
                    :disabled="hasAnswered || deleteMode"
                    placeholder="请输入你的答案"
                  />
                </div>

                <div v-if="showResult" class="result-box" :class="resultBoxClass">
                  <strong>{{ resultTitle }}</strong>
                  <span>参考答案：{{ displayAnswer(currentQuestion) }}</span>
                  <span v-if="showSelfEvaluationActions">填空题无法稳定自动判题，请根据参考答案自行评价。</span>
                  <el-button size="small" :icon="DocumentCopy" @click="openAnswerEditor">
                    修改答案
                  </el-button>
                </div>

                <div v-if="showExplanation && currentQuestion.explanation" class="explanation-box">
                  <h3>答案解析</h3>
                  <p>{{ currentQuestion.explanation }}</p>
                </div>

                <div v-if="aiExplanation" class="explanation-box ai">
                  <h3>AI 讲解</h3>
                  <p>{{ aiExplanation }}</p>
                </div>

                <div class="actions">
                  <template v-if="deleteMode">
                    <el-button type="danger" :icon="Delete" :loading="deleting" @click="deleteCurrentQuestion">
                      删除本题
                    </el-button>
                    <el-button @click="deleteMode = false">退出删题模式</el-button>
                  </template>
                  <template v-else>
                    <el-button :icon="ArrowLeft" :disabled="currentIndex <= 0" @click="goToPreviousQuestion">
                      上一题
                    </el-button>
                    <el-button :icon="ArrowRight" :disabled="currentIndex >= questions.length - 1" @click="goToNextQuestion">
                      下一题
                    </el-button>
                    <el-button
                      type="primary"
                      :icon="Select"
                      :disabled="!selectedAnswer || hasAnswered"
                      :loading="loading"
                      @click="submitCurrentAnswer"
                    >
                      提交
                    </el-button>
                    <el-button
                      v-if="pendingSubmissions.length > 0"
                      type="success"
                      :loading="batchSubmitting"
                      @click="submitAllPending"
                    >
                      批量提交 ({{ pendingSubmissions.length }})
                    </el-button>
                    <el-button :icon="Document" :disabled="!currentQuestion.explanation" @click="showExplanation = !showExplanation">
                      {{ showExplanation ? '隐藏解析' : '显示解析' }}
                    </el-button>
                    <el-button :icon="ChatDotRound" :loading="aiLoading" @click="loadAiExplanation">
                      AI讲解
                    </el-button>
                    <el-button
                      v-if="showSelfEvaluationActions"
                      type="success"
                      :loading="loading"
                      @click="submitSelfEvaluation(true)"
                    >
                      我答对了
                    </el-button>
                    <el-button
                      v-if="showSelfEvaluationActions"
                      type="danger"
                      plain
                      :loading="loading"
                      @click="submitSelfEvaluation(false)"
                    >
                      我答错了
                    </el-button>
                  </template>
                </div>
              </div>
            </section>
          </main>

          <footer class="stats-bar">
            <span>科目：{{ selectedSubject.name }}</span>
            <span>已完成 {{ completedCount }} / {{ questions.length }}</span>
            <span>正确率 {{ accuracyRate }}%</span>
          </footer>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowRight,
  Back,
  ChatDotRound,
  CircleCheck,
  CircleClose,
  Delete,
  Document,
  DocumentCopy,
  List,
  Plus,
  Refresh,
  Fold,
  Expand,
  Menu,
  Close,
  Select,
  Setting,
  Star,
  StarFilled
} from '@element-plus/icons-vue'
import {
  batchDeleteQuestions,
  batchSubmitAnswers,
  createSubject,
  deleteSubject as apiDeleteSubject,
  deleteQuestion as apiDeleteQuestion,
  getAiExplanation,
  getPlanItemsByDate,
  getQuestions,
  getSubjects,
  submitAnswer as apiSubmitAnswer,
  updatePlanItem,
  updateQuestionImportant,
  updateQuestionAnswer,
  updateQuestionType
} from '../api'

const route = useRoute()
const router = useRouter()
const username = ref(localStorage.getItem('auth_username') || '用户')
const navItems = [
  { path: '/', label: '练习模式', icon: Document },
  { path: '/plan', label: '学习计划', icon: List },
  { path: '/import', label: '导入习题', icon: Plus },
  { path: '/wrong', label: '错题本', icon: CircleClose },
  { path: '/review', label: '复习模式', icon: Refresh },
  { path: '/important', label: '重点题', icon: Star },
  { path: '/trash', label: '垃圾桶', icon: Delete },
  { path: '/settings', label: '设置', icon: Setting }
]

const subjects = ref([])
const selectedSubject = ref(null)
const newSubjectName = ref('')
const subjectCreating = ref(false)
const subjectDeletingId = ref(null)
const allQuestions = ref([])
const questions = ref([])
const currentIndex = ref(0)
const selectedAnswer = ref('')
const answers = ref({})
const showResult = ref(false)
const showExplanation = ref(false)
const deleteMode = ref(false)
const deleting = ref(false)
const batchDeleting = ref(false)
const batchSelectedIds = ref([])
const typeUpdating = ref(false)
const importantUpdating = ref(false)
const loading = ref(false)
const aiLoading = ref(false)
const aiExplanation = ref('')
const selectedQuestionType = ref('all')
const questionListRef = ref(null)
const answerEditValue = ref('')
const todayPlanDate = ref('')
const todayPlanItems = ref([])
const planLoading = ref(false)
const planPanelCollapsed = ref(false)
const planFloatCollapsed = ref(false)
const planFloatPosition = ref({ left: 0, top: 0 })
const planFloatDragging = ref(false)
const planFloatDragOffset = ref({ x: 0, y: 0 })
const PLAN_FLOAT_STORAGE_KEY = 'home_plan_float_position'
const PLAN_FLOAT_COLLAPSED_KEY = 'home_plan_float_collapsed'
const SIDEBAR_COLLAPSED_KEY = 'home_sidebar_collapsed'
const pendingSubmissions = ref([])
const batchSubmitting = ref(false)
const practiceMode = ref('sequential')
const practiceQuestionCount = ref(20)
const sidebarCollapsed = ref(false)
const mobileNavOpen = ref(false)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

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

const getLocalDateString = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const saveSidebarState = () => {
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed.value))
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  saveSidebarState()
}

const toggleMobileNav = () => {
  mobileNavOpen.value = !mobileNavOpen.value
}

const closeMobileNav = () => {
  mobileNavOpen.value = false
}

const syncLayoutMode = () => {
  viewportWidth.value = window.innerWidth
  if (isMobileNav.value) {
    mobileNavOpen.value = false
    sidebarCollapsed.value = false
    return
  }

  try {
    const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
    sidebarCollapsed.value = stored === 'true'
  } catch (error) {
    sidebarCollapsed.value = false
  }
}

const formatPlanDate = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(`${dateStr}T00:00:00`)
  return date.toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric', weekday: 'long' })
}

const showPlanFloat = computed(() => !selectedSubject.value)
const isMobileNav = computed(() => viewportWidth.value <= 960)
const planFloatStyle = computed(() => ({
  left: `${planFloatPosition.value.left}px`,
  top: `${planFloatPosition.value.top}px`
}))

const clampPlanFloatPosition = (left, top) => {
  const width = window.innerWidth
  const height = window.innerHeight
  const maxLeft = Math.max(width - 56, 16)
  const maxTop = Math.max(height - 56, 16)
  return {
    left: Math.min(Math.max(left, 16), maxLeft),
    top: Math.min(Math.max(top, 16), maxTop)
  }
}

const initPlanFloatPosition = () => {
  const fallback = clampPlanFloatPosition(window.innerWidth - 360, window.innerHeight - 320)
  try {
    const stored = localStorage.getItem(PLAN_FLOAT_STORAGE_KEY)
    if (stored) {
      const parsed = JSON.parse(stored)
      if (typeof parsed?.left === 'number' && typeof parsed?.top === 'number') {
        planFloatPosition.value = clampPlanFloatPosition(parsed.left, parsed.top)
      }
    }
  } catch (error) {
    // Ignore invalid stored coordinates and fall back below.
  }
  
  try {
    const collapsedStored = localStorage.getItem(PLAN_FLOAT_COLLAPSED_KEY)
    planFloatCollapsed.value = collapsedStored === 'true'
  } catch (error) {
    planFloatCollapsed.value = false
  }
  
  if (!planFloatPosition.value.left && !planFloatPosition.value.top) {
    planFloatPosition.value = fallback
  }
}

const togglePlanFloat = () => {
  planFloatCollapsed.value = !planFloatCollapsed.value
  localStorage.setItem(PLAN_FLOAT_COLLAPSED_KEY, String(planFloatCollapsed.value))
  if (planFloatCollapsed.value) {
    planFloatPosition.value = { left: window.innerWidth - 48, top: window.innerHeight / 2 - 30 }
    savePlanFloatPosition()
  }
}

const savePlanFloatPosition = () => {
  localStorage.setItem(PLAN_FLOAT_STORAGE_KEY, JSON.stringify(planFloatPosition.value))
}

const movePlanFloat = (event) => {
  if (!planFloatDragging.value) return
  planFloatPosition.value = clampPlanFloatPosition(
    event.clientX - planFloatDragOffset.value.x,
    event.clientY - planFloatDragOffset.value.y
  )
}

const endPlanFloatDrag = () => {
  if (!planFloatDragging.value) return
  planFloatDragging.value = false
  savePlanFloatPosition()
  window.removeEventListener('pointermove', movePlanFloat)
  window.removeEventListener('pointerup', endPlanFloatDrag)
}

const startPlanFloatDrag = (event) => {
  if (event.button !== undefined && event.button !== 0) return
  if (event.target?.closest?.('button')) return
  const floatEl = event.currentTarget?.closest?.('.plan-float')
  if (!floatEl) return

  const rect = floatEl.getBoundingClientRect()
  planFloatDragging.value = true
  planFloatDragOffset.value = {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }

  window.addEventListener('pointermove', movePlanFloat)
  window.addEventListener('pointerup', endPlanFloatDrag)
  event.preventDefault()
}

const editableTypeOptions = [
  { label: '单选题', value: 'single' },
  { label: '多选题', value: 'multi' },
  { label: '判断题', value: 'judge' },
  { label: '填空题', value: 'fill' },
  { label: '简答题', value: 'short' },
  { label: '编程题', value: 'code' }
]
const questionTypeOptions = [
  { label: '全部', value: 'all' },
  ...editableTypeOptions
]

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
  return Object.keys(currentQuestion.value.options || {}).sort().map((key) => ({
    key,
    value: currentQuestion.value.options[key]
  }))
})
const selectedAnswerList = computed({
  get: () => {
    if (!isMultiQuestion.value) return []
    return selectedAnswer.value ? selectedAnswer.value.split('') : []
  },
  set: (value) => {
    selectedAnswer.value = Array.isArray(value) ? value.slice().sort().join('') : ''
  }
})
const currentMultiAnswerSet = computed(() => new Set((currentQuestion.value?.answer || '').split('').filter(Boolean)))
const attachmentOptions = computed(() => currentQuestion.value?.options || {})
const attachmentSourceUrl = computed(() => attachmentOptions.value?._asset_url || '')
const attachmentDownloadUrl = computed(() => attachmentOptions.value?._asset_download_url || attachmentSourceUrl.value || '')
const attachmentName = computed(() => attachmentOptions.value?._asset_name || currentQuestion.value?.content || '附件')
const attachmentExt = computed(() => {
  const filename = String(attachmentName.value || '').toLowerCase()
  const dotIndex = filename.lastIndexOf('.')
  return dotIndex >= 0 ? filename.slice(dotIndex) : ''
})
const hasAttachmentAsset = computed(() => currentQuestion.value?.type === 'code' && Boolean(attachmentSourceUrl.value || attachmentDownloadUrl.value))
const isImageAttachment = computed(() => ['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif'].includes(attachmentExt.value))
const isPdfAttachment = computed(() => attachmentExt.value === '.pdf')
const isPreviewableAttachment = computed(() => isImageAttachment.value || isPdfAttachment.value)
const currentAnswerState = computed(() => answers.value[currentIndex.value] || null)
const showSelfEvaluationActions = computed(() => Boolean(currentAnswerState.value?.isPending))
const resultBoxClass = computed(() => {
  if (currentAnswerState.value?.isPending) return 'pending'
  return currentAnswerState.value?.isCorrect ? 'correct' : 'wrong'
})
const resultTitle = computed(() => {
  if (currentAnswerState.value?.isPending) return '已显示参考答案，请自行判断正误'
  return currentAnswerState.value?.isCorrect ? '回答正确' : '回答错误'
})
const hasAnswered = computed(() => answers.value[currentIndex.value] !== undefined)
const completedCount = computed(() => Object.values(answers.value).filter((item) => !item.isPending).length)
const accuracyRate = computed(() => {
  if (!completedCount.value) return 0
  const correct = Object.values(answers.value).filter((item) => !item.isPending && item.isCorrect).length
  return Math.round((correct / completedCount.value) * 100)
})

const normalizePracticeQuestionCount = () => {
  const total = allQuestions.value.length
  if (!total) {
    practiceQuestionCount.value = 1
    return 0
  }

  const numericCount = Number(practiceQuestionCount.value)
  const fallback = total
  const normalized = Number.isFinite(numericCount) ? Math.floor(numericCount) : fallback
  practiceQuestionCount.value = Math.min(Math.max(normalized || fallback, 1), total)
  return practiceQuestionCount.value
}

const shuffleQuestions = (source) => {
  const items = [...source]
  for (let i = items.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[items[i], items[j]] = [items[j], items[i]]
  }
  return items
}

const resetPracticeState = () => {
  currentIndex.value = 0
  selectedAnswer.value = ''
  answers.value = {}
  showResult.value = false
  showExplanation.value = false
  deleteMode.value = false
  deleting.value = false
  batchDeleting.value = false
  batchSelectedIds.value = []
  loading.value = false
  aiLoading.value = false
  aiExplanation.value = ''
  pendingSubmissions.value = []
}

const applyPracticeQuestions = (preferredQuestionId = Number(route.query.question_id) || null) => {
  const count = normalizePracticeQuestionCount()
  const sourceQuestions = allQuestions.value

  if (!sourceQuestions.length || count === 0) {
    questions.value = []
    resetPracticeState()
    return
  }

  let sessionQuestions = []
  if (practiceMode.value === 'random') {
    const preferredQuestion = preferredQuestionId
      ? sourceQuestions.find((question) => question.id === preferredQuestionId)
      : null
    const remainingQuestions = preferredQuestion
      ? sourceQuestions.filter((question) => question.id !== preferredQuestionId)
      : sourceQuestions
    sessionQuestions = shuffleQuestions(remainingQuestions).slice(0, Math.max(count - (preferredQuestion ? 1 : 0), 0))
    if (preferredQuestion) {
      sessionQuestions.unshift(preferredQuestion)
    }
  } else {
    sessionQuestions = sourceQuestions.slice(0, count)
  }

  questions.value = sessionQuestions
  resetPracticeState()

  const questionIndex = preferredQuestionId
    ? questions.value.findIndex((question) => question.id === preferredQuestionId)
    : -1
  selectQuestion(questionIndex >= 0 ? questionIndex : 0)
}

const truncateContent = (content) => (content.length > 28 ? `${content.slice(0, 28)}...` : content)
const questionTypeLabel = (type) => ({
  single: '单选题',
  multi: '多选题',
  judge: '判断题',
  fill: '填空题',
  short: '简答题',
  code: '编程题'
}[type] || '题目')
const displayAnswer = (question) => {
  if (!question) return ''
  if (question.type === 'judge') {
    return question.answer === 'T' ? '正确' : question.answer === 'F' ? '错误' : question.answer
  }
  if (question.type === 'multi') {
    return question.answer.split('').join('、')
  }
  return question.answer
}

const normalizeDisplayedAnswerInput = (question) => {
  if (!question) return ''
  if (question.type === 'multi') {
    return question.answer.split('').join('')
  }
  if (question.type === 'judge') {
    return question.answer === 'T' ? 'T' : question.answer === 'F' ? 'F' : question.answer
  }
  return question.answer || ''
}

const openAttachment = () => {
  if (!attachmentSourceUrl.value) return
  window.open(attachmentSourceUrl.value, '_blank', 'noopener,noreferrer')
}

const downloadAttachment = () => {
  if (!attachmentDownloadUrl.value) return
  const link = document.createElement('a')
  link.href = attachmentDownloadUrl.value
  link.download = attachmentName.value || 'attachment'
  link.rel = 'noopener'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const loadSubjects = async () => {
  try {
    subjects.value = await getSubjects()
  } catch (error) {
    ElMessage.error(`加载科目失败：${error.response?.data?.detail || error.message}`)
  }
}

const handleCreateSubject = async () => {
  if (!newSubjectName.value.trim()) {
    ElMessage.warning('请输入科目名称')
    return
  }
  subjectCreating.value = true
  try {
    const subject = await createSubject(newSubjectName.value.trim())
    newSubjectName.value = ''
    await loadSubjects()
    enterSubject(subject)
  } catch (error) {
    ElMessage.error(`创建科目失败：${error.response?.data?.detail || error.message}`)
  } finally {
    subjectCreating.value = false
  }
}

const enterSubject = async (subject) => {
  selectedSubject.value = subject
  router.replace({ path: '/', query: { subject_id: subject.id } })
  await loadQuestions()
}

const handleDeleteSubject = async (subject) => {
  if (!subject || subjectDeletingId.value) return
  try {
    await ElMessageBox.confirm(
      `确认删除练习集「${subject.name}」？该练习集下的题目、练习记录和错题记录都会一起删除，且无法恢复。`,
      '删除练习集',
      {
        type: 'warning',
        confirmButtonText: '确认删除',
        cancelButtonText: '取消'
      }
    )
    subjectDeletingId.value = subject.id
    await apiDeleteSubject(subject.id)
    if (selectedSubject.value?.id === subject.id) {
      selectedSubject.value = null
      questions.value = []
      answers.value = {}
      batchSelectedIds.value = []
      deleteMode.value = false
      router.replace({ path: '/' })
    }
    await loadSubjects()
    ElMessage.success('练习集已删除')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`删除练习集失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    subjectDeletingId.value = null
  }
}

const backToSubjects = () => {
  selectedSubject.value = null
  allQuestions.value = []
  questions.value = []
  router.replace({ path: '/' })
  loadSubjects()
  loadTodayPlan()
}

const loadQuestions = async () => {
  if (!selectedSubject.value) return
  try {
    allQuestions.value = await getQuestions(0, 1000, selectedSubject.value.id, selectedQuestionType.value)
    if (allQuestions.value.length && practiceQuestionCount.value > allQuestions.value.length) {
      practiceQuestionCount.value = allQuestions.value.length
    }
    applyPracticeQuestions()
  } catch (error) {
    ElMessage.error(`加载题目失败：${error.response?.data?.detail || error.message}`)
  }
}

const loadTodayPlan = async () => {
  planLoading.value = true
  try {
    todayPlanDate.value = getLocalDateString()
    const items = await getPlanItemsByDate(todayPlanDate.value)
    todayPlanItems.value = items.filter((item) => item.completed !== 1)
  } catch (error) {
    todayPlanItems.value = []
  } finally {
    planLoading.value = false
  }
}

const refreshTodayPlan = () => {
  if (!selectedSubject.value) {
    loadTodayPlan()
  }
}

const completePlanItem = async (item) => {
  try {
    await updatePlanItem(item.id, { completed: 1 })
    const index = todayPlanItems.value.findIndex(i => i.id === item.id)
    if (index > -1) {
      todayPlanItems.value.splice(index, 1)
    }
    ElMessage.success('🎉 任务完成！')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const updateCurrentQuestionType = async (type) => {
  if (!currentQuestion.value) return
  typeUpdating.value = true
  try {
    const updated = await updateQuestionType(currentQuestion.value.id, type)
    questions.value[currentIndex.value] = updated
    selectedAnswer.value = ''
    showResult.value = false
    showExplanation.value = false
    aiExplanation.value = ''
    ElMessage.success('题型已更新')
  } catch (error) {
    ElMessage.error(`修改题型失败：${error.response?.data?.detail || error.message}`)
    await loadQuestions()
  } finally {
    typeUpdating.value = false
  }
}

const toggleCurrentImportant = async () => {
  if (!currentQuestion.value) return
  importantUpdating.value = true
  try {
    const updated = await updateQuestionImportant(currentQuestion.value.id, !currentQuestion.value.is_important)
    questions.value[currentIndex.value] = updated
    ElMessage.success(updated.is_important ? '已标记为重点题' : '已取消重点标记')
  } catch (error) {
    ElMessage.error(`更新重点标记失败：${error.response?.data?.detail || error.message}`)
  } finally {
    importantUpdating.value = false
  }
}

const openAnswerEditor = async () => {
  if (!currentQuestion.value) return
  answerEditValue.value = normalizeDisplayedAnswerInput(currentQuestion.value)
  try {
    const { value } = await ElMessageBox.prompt(
      currentQuestion.value.type === 'multi'
        ? '请输入标准答案，多个选项直接连写，如 ABC'
        : currentQuestion.value.type === 'judge'
          ? '请输入标准答案：T 或 F'
          : '请输入标准答案',
      '修改答案',
      {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputValue: answerEditValue.value,
        inputPlaceholder: currentQuestion.value.type === 'multi' ? 'ABC' : currentQuestion.value.type === 'judge' ? 'T / F' : '答案'
      }
    )
    const updated = await updateQuestionAnswer(currentQuestion.value.id, value)
    questions.value[currentIndex.value] = updated
    ElMessage.success('答案已更新')
    if (showResult.value) {
      delete answers.value[currentIndex.value]
      showResult.value = false
      showExplanation.value = false
      ElMessage.info('请重新提交当前题以按新答案判定')
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`修改答案失败：${error.response?.data?.detail || error.message}`)
    }
  }
}

const selectQuestion = (index) => {
  currentIndex.value = Math.max(0, Math.min(index, Math.max(questions.value.length - 1, 0)))
  const savedAnswer = answers.value[currentIndex.value]
  selectedAnswer.value = savedAnswer?.userAnswer || ''
  showResult.value = Boolean(savedAnswer)
  showExplanation.value = Boolean(savedAnswer)
  aiExplanation.value = ''
  scrollCurrentQuestionIntoView('smooth')
}

const goToPreviousQuestion = () => {
  if (currentIndex.value <= 0) return
  selectQuestion(currentIndex.value - 1)
}

const goToNextQuestion = () => {
  if (currentIndex.value >= questions.value.length - 1) return
  selectQuestion(currentIndex.value + 1)
}

const handlePracticeEnterKey = (event) => {
  if (event.key !== 'Enter' || event.shiftKey || event.ctrlKey || event.altKey || event.metaKey) return
  if (!selectedSubject.value || !currentQuestion.value || deleteMode.value) return
  if (loading.value || hasAnswered.value || !selectedAnswer.value) return
  if (event.isComposing) return

  const target = event.target
  const tagName = target?.tagName
  if (tagName === 'TEXTAREA') return
  if (target?.closest?.('.el-message-box')) return

  event.preventDefault()
  submitCurrentAnswer()
}

const scrollCurrentQuestionIntoView = (behavior = 'smooth') => {
  nextTick(() => {
    const container = questionListRef.value
    if (!container) return
    const target = container.querySelector(`.question-item[data-index="${currentIndex.value}"]`)
    target?.scrollIntoView({ behavior, block: 'nearest' })
  })
}

const submitCurrentAnswer = async () => {
  if (!selectedAnswer.value || !currentQuestion.value) return
  
  const isFillQuestion = currentQuestion.value.type === 'fill'
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

  answers.value[currentIndex.value] = {
    isCorrect: null,
    isPending: true,
    userAnswer: selectedAnswer.value
  }
  showResult.value = true
  showExplanation.value = true

  if (isFillQuestion) {
    ElMessage.info('已显示参考答案，请自行判断是否答对')
  } else {
    ElMessage.success('答案已保存，将在批量提交时统一处理')
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
  loading.value = true
  
  try {
    const result = await batchSubmitAnswers(pendingSubmissions.value)
    
    result.results.forEach(res => {
      if (res.error) {
        ElMessage.error(`第 ${res.question_id} 题提交失败: ${res.error}`)
        return
      }
      
      const submission = pendingSubmissions.value.find(s => s.question_id === res.question_id)
      if (submission) {
        answers.value[submission.index] = {
          isCorrect: res.is_correct,
          isPending: false,
          userAnswer: submission.user_answer
        }
      }
      
      if (res.is_correct) {
        if (res.removed_from_wrong) {
          ElMessage.success(`回答正确，已从错题本移除`)
        } else if (res.remaining_to_remove > 0) {
          ElMessage.success(`回答正确，还需再答对 ${res.remaining_to_remove} 次才会移出错题本`)
        }
      }
    })
    
    pendingSubmissions.value = []
    ElMessage.success(`批量提交完成，共提交 ${result.results.length} 题`)
  } catch (error) {
    ElMessage.error(`批量提交失败：${error.response?.data?.detail || error.message}`)
  } finally {
    batchSubmitting.value = false
    loading.value = false
  }
}

const submitSelfEvaluation = async (isCorrect) => {
  if (!currentQuestion.value || !currentAnswerState.value?.isPending) return
  loading.value = true
  try {
    const result = await apiSubmitAnswer(currentQuestion.value.id, currentAnswerState.value.userAnswer, isCorrect)
    answers.value[currentIndex.value] = {
      isCorrect: result.is_correct,
      isPending: false,
      userAnswer: currentAnswerState.value.userAnswer
    }
    showResult.value = true
    showExplanation.value = true
    if (result.is_correct) {
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

const deleteCurrentQuestion = async () => {
  if (!currentQuestion.value) return
  try {
    await ElMessageBox.confirm('确认删除这道题？相关练习记录和错题记录也会一起删除。', '删除题目', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    })
    deleting.value = true
    const removedIndex = currentIndex.value
    const removedId = currentQuestion.value.id
    await apiDeleteQuestion(currentQuestion.value.id)
    questions.value.splice(removedIndex, 1)
    answers.value = {}
    batchSelectedIds.value = batchSelectedIds.value.filter((id) => id !== removedId)
    selectQuestion(Math.min(removedIndex, questions.value.length - 1))
    ElMessage.success('题目已移入垃圾桶')
    await loadSubjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`删除失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    deleting.value = false
  }
}

const toggleBatchSelection = (questionId) => {
  if (batchSelectedIds.value.includes(questionId)) {
    batchSelectedIds.value = batchSelectedIds.value.filter((id) => id !== questionId)
  } else {
    batchSelectedIds.value = [...batchSelectedIds.value, questionId]
  }
}

const selectAllForBatch = () => {
  batchSelectedIds.value = questions.value.map((question) => question.id)
}

const batchDeleteSelected = async () => {
  if (!batchSelectedIds.value.length) return
  try {
    await ElMessageBox.confirm(`确认将选中的 ${batchSelectedIds.value.length} 道题移入垃圾桶？`, '批量删除题目', {
      type: 'warning',
      confirmButtonText: '确认删除',
      cancelButtonText: '取消'
    })
    batchDeleting.value = true
    await batchDeleteQuestions(batchSelectedIds.value)
    const deletedIds = new Set(batchSelectedIds.value)
    questions.value = questions.value.filter((question) => !deletedIds.has(question.id))
    batchSelectedIds.value = []
    answers.value = {}
    selectQuestion(Math.min(currentIndex.value, questions.value.length - 1))
    ElMessage.success('所选题目已移入垃圾桶')
    await loadSubjects()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`批量删除失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    batchDeleting.value = false
  }
}

const loadAiExplanation = async () => {
  if (!currentQuestion.value) return
  aiLoading.value = true
  try {
    const result = await getAiExplanation(currentQuestion.value.id)
    aiExplanation.value = result.explanation
    if (result.source === 'local') {
      ElMessage.info('未配置 DeepSeek API Key，已显示本地解析')
    }
  } catch (error) {
    ElMessage.error(`AI讲解失败：${error.response?.data?.detail || error.message}`)
  } finally {
    aiLoading.value = false
  }
}

const resetPractice = () => {
  applyPracticeQuestions()
}

watch(currentIndex, () => {
  scrollCurrentQuestionIntoView('smooth')
})

onMounted(async () => {
  window.addEventListener('keydown', handlePracticeEnterKey)
  window.addEventListener('resize', initPlanFloatPosition)
  window.addEventListener('resize', syncLayoutMode)
  await loadSubjects()
  syncLayoutMode()
  initPlanFloatPosition()
  loadTodayPlan()
  const subjectId = Number(route.query.subject_id)
  if (subjectId) {
    const subject = subjects.value.find((item) => item.id === subjectId)
    if (subject) {
      selectedSubject.value = subject
      await loadQuestions()
    }
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handlePracticeEnterKey)
  window.removeEventListener('resize', initPlanFloatPosition)
  window.removeEventListener('resize', syncLayoutMode)
  window.removeEventListener('pointermove', movePlanFloat)
  window.removeEventListener('pointerup', endPlanFloatDrag)
})
</script>

<style scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
  background: linear-gradient(180deg, #f0f9ff 0%, #fafafa 100%);
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.sidebar {
  width: clamp(216px, 18vw, 240px);
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: white;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  z-index: 100;
  transition: width 0.25s ease, transform 0.25s ease;
}

.app-layout.sidebar-collapsed .sidebar {
  width: 84px;
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.logo-copy {
  min-width: 0;
}

.logo-copy span {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.sidebar-toggle {
  color: #cbd5e1;
}

.desktop-toggle {
  margin-left: auto;
}

.mobile-close {
  display: none;
}

.nav-section-title {
  padding: 0 16px 10px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  font-size: 40px;
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
  min-width: 20px;
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
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #e2e8f0;
  background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
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
  margin-left: clamp(216px, 18vw, 240px);
  min-width: 0;
  min-height: 100vh;
  transition: margin-left 0.25s ease;
}

.app-layout.sidebar-collapsed .main-content {
  margin-left: 84px;
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
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.header-main {
  min-width: 0;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.header-nav-btn {
  color: #334155;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}

.subject-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 8px 12px;
  border-radius: 999px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 13px;
}

.subject-chip span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.subject-page {
  max-width: 1180px;
  width: 100%;
  margin: 0 auto;
  padding: clamp(16px, 2vw, 24px);
}

.create-subject {
  max-width: none;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin: 0 0 20px;
  padding: 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
}

.subject-grid {
  max-width: none;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 14px;
}

.subject-card {
  min-height: 112px;
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 18px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.subject-card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.subject-card:hover {
  border-color: #409eff;
  background: #f5f9ff;
}

.subject-card strong {
  color: #303133;
  font-size: 18px;
}

.subject-card span {
  color: #909399;
}

.practice-layout {
  flex: 1;
  display: grid;
  grid-template-columns: minmax(280px, 26vw) minmax(0, 1fr);
  gap: clamp(14px, 1.8vw, 24px);
  padding: clamp(16px, 2vw, 24px);
}

.type-filter {
  padding: 16px clamp(16px, 2vw, 24px) 0;
  background: #f5f7fa;
}

.practice-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.practice-mode-controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
}

.count-input {
  width: 140px;
}

.plan-float {
  position: fixed;
  right: 24px;
  bottom: 92px;
  width: 320px;
  max-width: calc(100vw - 32px);
  z-index: 180;
  border-radius: 12px;
  background: #fff;
  color: #303133;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.12);
  border: 1px solid #e4e7ed;
  overflow: hidden;
  user-select: none;
  cursor: grab;
  transition: all 0.3s ease;
}

.plan-float.collapsed {
  width: 48px;
  min-width: 48px;
  max-width: 48px;
  border-radius: 12px 0 0 12px;
  box-shadow: -4px 0 16px rgba(15, 23, 42, 0.08);
}

.plan-float.collapsed .plan-float-content {
  display: none;
}

.plan-float-collapsed-trigger {
  display: none;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 0;
  cursor: pointer;
  color: #409eff;
  transition: all 0.2s ease;
}

.plan-float.collapsed .plan-float-collapsed-trigger {
  display: flex;
}

.plan-float-collapsed-trigger:hover {
  background: rgba(64, 158, 255, 0.1);
}

.plan-float-collapsed-label {
  font-size: 11px;
  margin-top: 4px;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  letter-spacing: 2px;
}

.plan-float-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #ebeef5;
  touch-action: none;
  background: linear-gradient(180deg, #f8fbff 0%, #fff 100%);
}

.plan-float-actions {
  display: flex;
  gap: 4px;
}

.plan-float-header p {
  margin: 0;
  font-size: 12px;
  color: #409eff;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.plan-float-header h3 {
  margin: 4px 0 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.plan-float-body {
  padding: 12px 14px 14px;
}

.plan-float-list {
  display: grid;
  gap: 10px;
  max-height: 190px;
  overflow-y: auto;
  padding-right: 4px;
}

.plan-float-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 12px;
  background: #f8fafc;
  color: #303133;
  line-height: 1.5;
}

.plan-float-item:hover {
  background: #f1f5f9;
  transform: translateX(4px);
}

.plan-float-item.completed {
  opacity: 0.6;
  text-decoration: line-through;
}

.plan-float-status {
  font-size: 16px;
  color: #409eff;
  flex-shrink: 0;
}

.plan-float-hint {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.plan-float-item:hover .plan-float-hint {
  opacity: 1;
}

.plan-float-item.completed .plan-float-status {
  color: #67c23a;
}

.plan-float-body::-webkit-scrollbar,
.plan-float-list::-webkit-scrollbar {
  width: 8px;
}

.plan-float-body::-webkit-scrollbar-track,
.plan-float-list::-webkit-scrollbar-track {
  background: #f5f7fa;
}

.plan-float-body::-webkit-scrollbar-thumb,
.plan-float-list::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 999px;
}

.plan-float-body::-webkit-scrollbar-thumb:hover,
.plan-float-list::-webkit-scrollbar-thumb:hover {
  background: #909399;
}

.question-list {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  align-self: start;
  min-width: 0;
  max-height: calc(100vh - 170px);
  display: flex;
  flex-direction: column;
}

.list-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  font-weight: 600;
  border-bottom: 1px solid #e4e7ed;
}

.batch-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #f0f2f5;
  background: #fff7f7;
}

.batch-bar span {
  color: #606266;
  font-size: 13px;
}

.question-item {
  width: 100%;
  min-height: 56px;
  display: grid;
  grid-template-columns: 34px 1fr 20px 22px;
  align-items: center;
  gap: 10px;
  border: 0;
  border-bottom: 1px solid #f0f2f5;
  background: #fff;
  padding: 10px 14px;
  text-align: left;
  cursor: pointer;
}

.question-item.active {
  background: #ecf5ff;
}

.question-item.deleting.active {
  background: #fef0f0;
}

.question-item.deleting {
  grid-template-columns: 34px 24px 1fr 20px 22px;
}

.important-star {
  color: #e6a23c;
}

.question-item.done:not(.active) {
  background: #fafafa;
}

.question-number {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f4f4f5;
  font-weight: 600;
}

.question-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #606266;
}

.status.correct {
  color: #67c23a;
}

.status.pending {
  color: #409eff;
}

.status.wrong {
  color: #f56c6c;
}

.question-panel {
  min-width: 0;
}

.question-card {
  width: min(100%, 860px);
  margin: 0 auto;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  padding: clamp(18px, 2vw, 24px);
}

.question-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: #909399;
  margin-bottom: 18px;
}

.meta-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.type-editor {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.question-type-select {
  width: 112px;
}

.question-content {
  padding: 18px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 18px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  margin-bottom: 18px;
}

.attachment-panel {
  display: grid;
  gap: 14px;
  margin-bottom: 18px;
  padding: 16px;
  border: 1px solid #dbeafe;
  border-radius: 10px;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.attachment-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.attachment-header strong {
  display: block;
  margin-bottom: 6px;
  color: #1f2937;
}

.attachment-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.attachment-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.attachment-image,
.attachment-frame {
  width: 100%;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
}

.attachment-image {
  max-height: 520px;
  object-fit: contain;
}

.attachment-frame {
  min-height: 520px;
}

.options {
  display: grid;
  gap: 12px;
  margin-bottom: 18px;
}

.text-answer {
  margin-bottom: 18px;
}

.option-item {
  display: block;
  padding: 14px 16px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  cursor: pointer;
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
  margin-right: 8px;
}

.result-box,
.explanation-box {
  display: grid;
  gap: 8px;
  padding: 14px 16px;
  border-radius: 8px;
  margin-bottom: 16px;
  line-height: 1.7;
}

.result-box.correct {
  background: #f0f9eb;
  color: #529b2e;
}

.result-box.pending {
  background: #ecf5ff;
  color: #1d4ed8;
}

.result-box.wrong {
  background: #fef0f0;
  color: #c45656;
}

.explanation-box {
  background: #f8fafc;
  color: #606266;
}

.explanation-box.ai {
  background: #fdf6ec;
}

.explanation-box h3 {
  margin: 0;
  font-size: 15px;
  color: #303133;
}

.explanation-box p {
  margin: 0;
  white-space: pre-wrap;
}

.stats-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px 32px;
  padding: 14px 24px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  color: #606266;
}

@media (max-width: 1180px) {
  .question-list {
    max-height: calc(100vh - 156px);
  }

  .question-summary {
    font-size: 13px;
  }
}

@media (max-width: 960px) {
  .sidebar {
    position: fixed;
    width: min(82vw, 320px);
    max-width: 320px;
    height: 100vh;
    transform: translateX(-100%);
    box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22);
  }

  .app-layout.mobile-nav-open .sidebar {
    transform: translateX(0);
  }

  .app-layout.sidebar-collapsed .sidebar {
    width: min(82vw, 320px);
  }

  .main-content {
    margin-left: 0;
  }

  .mobile-close {
    display: inline-flex;
    margin-left: auto;
  }

  .nav-menu {
    display: block;
    padding: 12px 16px 14px;
    overflow-x: hidden;
    overflow-y: auto;
  }

  .nav-item {
    margin-bottom: 4px;
  }

  .user-section {
    padding: 12px 16px 16px;
  }

  .practice-layout {
    grid-template-columns: 1fr;
  }

  .practice-toolbar {
    align-items: stretch;
  }

  .practice-mode-controls {
    width: 100%;
    justify-content: flex-start;
  }

  .question-list {
    max-height: 280px;
  }

  .create-subject {
    grid-template-columns: 1fr;
  }

  .page-header,
  .stats-bar {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .attachment-header {
    flex-direction: column;
  }
}

@media (max-width: 720px) {
  .page-header h1 {
    font-size: 20px;
  }

  .header-actions,
  .actions,
  .practice-mode-controls {
    width: 100%;
  }

  .practice-mode-controls > * {
    flex: 1 1 auto;
  }

  .count-input {
    width: 100%;
  }

  .question-card {
    width: 100%;
  }

  .meta-right {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 560px) {
  .logo-section {
    padding: 16px 14px 10px;
  }

  .logo-icon {
    font-size: 32px;
    margin-bottom: 8px;
  }

  .nav-menu {
    padding: 10px 14px 12px;
  }

  .nav-item {
    padding: 10px 12px;
    gap: 8px;
  }

  .nav-item span {
    font-size: 13px;
  }

  .question-list {
    max-height: 250px;
  }

  .question-item,
  .question-item.deleting {
    gap: 8px;
    padding: 10px 12px;
  }

  .question-item {
    grid-template-columns: 30px minmax(0, 1fr) 18px 18px;
  }

  .question-item.deleting {
    grid-template-columns: 30px 22px minmax(0, 1fr) 18px 18px;
  }

  .question-number {
    width: 24px;
    height: 24px;
    font-size: 12px;
  }

  .question-content {
    padding: 14px;
    font-size: 16px;
    line-height: 1.7;
  }

  .stats-bar {
    justify-content: flex-start;
    padding: 12px 16px;
  }
}
</style>
