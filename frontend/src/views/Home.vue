<template>
  <div class="practice-page">
    <header class="page-header">
      <div>
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
        <el-segmented v-model="selectedQuestionType" :options="questionTypeOptions" @change="loadQuestions" />
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

            <div v-if="showResult" class="result-box" :class="answers[currentIndex]?.isCorrect ? 'correct' : 'wrong'">
              <strong>{{ answers[currentIndex]?.isCorrect ? '回答正确' : '回答错误' }}</strong>
              <span>参考答案：{{ displayAnswer(currentQuestion) }}</span>
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
                <el-button :icon="Document" :disabled="!currentQuestion.explanation" @click="showExplanation = !showExplanation">
                  {{ showExplanation ? '隐藏解析' : '显示解析' }}
                </el-button>
                <el-button :icon="ChatDotRound" :loading="aiLoading" @click="loadAiExplanation">
                  AI讲解
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
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft, ArrowRight, Back, ChatDotRound, CircleCheck, CircleClose, Delete, Document, DocumentCopy, Plus, Refresh, Select, Star, StarFilled } from '@element-plus/icons-vue'
import {
  batchDeleteQuestions,
  createSubject,
  deleteSubject as apiDeleteSubject,
  deleteQuestion as apiDeleteQuestion,
  getAiExplanation,
  getQuestions,
  getSubjects,
  submitAnswer as apiSubmitAnswer,
  updateQuestionImportant,
  updateQuestionAnswer,
  updateQuestionType
} from '../api'

const route = useRoute()
const router = useRouter()
const subjects = ref([])
const selectedSubject = ref(null)
const newSubjectName = ref('')
const subjectCreating = ref(false)
const subjectDeletingId = ref(null)
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
const hasAnswered = computed(() => answers.value[currentIndex.value] !== undefined)
const completedCount = computed(() => Object.keys(answers.value).length)
const accuracyRate = computed(() => {
  if (!completedCount.value) return 0
  const correct = Object.values(answers.value).filter((item) => item.isCorrect).length
  return Math.round((correct / completedCount.value) * 100)
})

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
  questions.value = []
  router.replace({ path: '/' })
  loadSubjects()
}

const loadQuestions = async () => {
  if (!selectedSubject.value) return
  try {
    questions.value = await getQuestions(0, 1000, selectedSubject.value.id, selectedQuestionType.value)
    currentIndex.value = 0
    answers.value = {}
    batchSelectedIds.value = []
    const questionId = Number(route.query.question_id)
    const questionIndex = questionId ? questions.value.findIndex((question) => question.id === questionId) : -1
    selectQuestion(questionIndex >= 0 ? questionIndex : 0)
  } catch (error) {
    ElMessage.error(`加载题目失败：${error.response?.data?.detail || error.message}`)
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
  selectedAnswer.value = answers.value[currentIndex.value]?.userAnswer || ''
  showResult.value = Boolean(answers.value[currentIndex.value])
  showExplanation.value = Boolean(answers.value[currentIndex.value])
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
  loading.value = true
  try {
    const result = await apiSubmitAnswer(currentQuestion.value.id, selectedAnswer.value)
    answers.value[currentIndex.value] = {
      isCorrect: result.is_correct,
      userAnswer: selectedAnswer.value
    }
    showResult.value = true
    showExplanation.value = true
    if (result.is_correct) {
      if (result.removed_from_wrong) {
        ElMessage.success('回答正确，已从错题本移除')
      } else if (result.remaining_to_remove > 0) {
        ElMessage.success(`回答正确，还需再答对 ${result.remaining_to_remove} 次才会移出错题本`)
      } else {
        ElMessage.success('回答正确')
      }
      if (currentIndex.value < questions.value.length - 1) {
        selectQuestion(currentIndex.value + 1)
      }
    } else {
      ElMessage.warning('回答错误，已加入错题本')
    }
  } catch (error) {
    ElMessage.error(`提交失败：${error.response?.data?.detail || error.message}`)
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
  answers.value = {}
  selectQuestion(0)
}

watch(currentIndex, () => {
  scrollCurrentQuestionIntoView('smooth')
})

onMounted(async () => {
  window.addEventListener('keydown', handlePracticeEnterKey)
  await loadSubjects()
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
})
</script>

<style scoped>
.practice-page {
  min-height: calc(100vh - 49px);
  display: flex;
  flex-direction: column;
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
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.subject-page {
  padding: 20px;
}

.create-subject {
  max-width: 720px;
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin: 0 auto 20px;
  padding: 18px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.subject-grid {
  max-width: 980px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
}

.subject-card {
  min-height: 112px;
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 18px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
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
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 20px;
  padding: 20px;
}

.type-filter {
  padding: 16px 20px 0;
  background: #f5f7fa;
}

.question-list {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  overflow-y: auto;
  overflow-x: hidden;
  scroll-behavior: smooth;
  align-self: start;
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

.status.wrong {
  color: #f56c6c;
}

.question-panel {
  min-width: 0;
}

.question-card {
  max-width: 860px;
  margin: 0 auto;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 24px;
}

.question-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
  gap: 10px;
}

.question-type-select {
  width: 112px;
}

.question-content {
  padding: 18px;
  background: #fafafa;
  border-radius: 8px;
  font-size: 18px;
  line-height: 1.8;
  color: #303133;
  white-space: pre-wrap;
  margin-bottom: 18px;
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
  justify-content: center;
  gap: 48px;
  padding: 14px 24px;
  background: #fff;
  border-top: 1px solid #e4e7ed;
  color: #606266;
}

@media (max-width: 860px) {
  .practice-layout {
    grid-template-columns: 1fr;
  }

  .question-list {
    max-height: 260px;
  }

  .create-subject {
    grid-template-columns: 1fr;
  }
}
</style>
