<template>
  <div class="review-page">
    <header class="page-header">
      <div>
        <h1>复习模式</h1>
        <p>答对会自动移出错题本，答错会继续保留。</p>
      </div>
      <el-button :icon="Back" @click="$router.push({ path: '/wrong', query: subjectId ? { subject_id: subjectId } : {} })">返回错题本</el-button>
    </header>

    <main class="review-content">
      <section v-if="!reviewStarted" class="start-card">
        <div class="count-row">
          <span>抽取数量</span>
          <el-input-number v-model="reviewCount" :min="1" :max="50" />
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

        <div v-else class="text-answer">
          <el-input
            v-model="selectedAnswer"
            :type="['short', 'code'].includes(currentQuestion.type) ? 'textarea' : 'text'"
            :rows="currentQuestion.type === 'code' ? 8 : currentQuestion.type === 'short' ? 5 : 1"
            :disabled="showResult"
            placeholder="请输入你的答案"
          />
        </div>

        <div v-if="showResult" class="result-box" :class="currentResult?.is_correct ? 'correct' : 'wrong'">
          <strong>{{ reviewResultTitle }}</strong>
          <span>参考答案：{{ displayAnswer(currentQuestion) }}</span>
          <span v-if="currentQuestion.explanation">解析：{{ currentQuestion.explanation }}</span>
        </div>

        <div class="actions">
          <el-button
            v-if="!showResult"
            type="primary"
            :icon="Select"
            :disabled="!selectedAnswer"
            :loading="isSubmitting"
            @click="submitAnswer"
          >
            提交
          </el-button>
          <el-button v-else type="primary" :icon="ArrowRight" @click="nextQuestion">
            {{ currentIndex < reviewQuestions.length - 1 ? '下一题' : '查看总结' }}
          </el-button>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Back, Collection, Refresh, Select } from '@element-plus/icons-vue'
import { generateReviewQuestions, submitReviewAnswer } from '../api'

const STORAGE_KEY = 'exercise-review-session'
const route = useRoute()

const reviewCount = ref(10)
const subjectId = ref(null)
const reviewQuestions = ref([])
const currentIndex = ref(0)
const selectedAnswer = ref('')
const showResult = ref(false)
const currentResult = ref(null)
const isGenerating = ref(false)
const isSubmitting = ref(false)
const reviewStarted = ref(false)
const reviewFinished = ref(false)
const correctCount = ref(0)

const currentQuestion = computed(() => reviewQuestions.value[currentIndex.value])
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
const progressPercent = computed(() => {
  if (!reviewQuestions.value.length) return 0
  return Math.round(((currentIndex.value + 1) / reviewQuestions.value.length) * 100)
})
const accuracyPercent = computed(() => {
  if (!reviewQuestions.value.length) return 0
  return Math.round((correctCount.value / reviewQuestions.value.length) * 100)
})
const reviewResultTitle = computed(() => {
  if (!currentResult.value) return ''
  if (!currentResult.value.is_correct) return '答错，留在错题本'
  if (currentResult.value.removed_from_wrong) return '答对，已移出错题本'
  if (currentResult.value.remaining_to_remove > 0) {
    return `答对，还需再答对 ${currentResult.value.remaining_to_remove} 次才移出`
  }
  return '答对'
})
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

const saveSession = () => {
  if (!reviewStarted.value) return
  localStorage.setItem(STORAGE_KEY, JSON.stringify({
    reviewQuestions: reviewQuestions.value,
    currentIndex: currentIndex.value,
    selectedAnswer: selectedAnswer.value,
    showResult: showResult.value,
    currentResult: currentResult.value,
    reviewStarted: reviewStarted.value,
    reviewFinished: reviewFinished.value,
    correctCount: correctCount.value
  }))
}

const restoreSession = () => {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return false
  try {
    const session = JSON.parse(raw)
    if (!Array.isArray(session.reviewQuestions) || !session.reviewQuestions.length) return false
    reviewQuestions.value = session.reviewQuestions
    currentIndex.value = session.currentIndex || 0
    selectedAnswer.value = session.selectedAnswer || ''
    showResult.value = Boolean(session.showResult)
    currentResult.value = session.currentResult || null
    reviewStarted.value = Boolean(session.reviewStarted)
    reviewFinished.value = Boolean(session.reviewFinished)
    correctCount.value = session.correctCount || 0
    return true
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return false
  }
}

const clearSession = () => {
  localStorage.removeItem(STORAGE_KEY)
}

const startReview = async () => {
  isGenerating.value = true
  try {
    const questions = await generateReviewQuestions(reviewCount.value, subjectId.value)
    if (!questions.length) {
      ElMessage.info('错题本中没有可复习的题目')
      return
    }
    reviewQuestions.value = questions
    currentIndex.value = 0
    selectedAnswer.value = ''
    showResult.value = false
    currentResult.value = null
    correctCount.value = 0
    reviewStarted.value = true
    reviewFinished.value = false
    saveSession()
  } catch (error) {
    ElMessage.error(`生成复习题失败：${error.response?.data?.detail || error.message}`)
  } finally {
    isGenerating.value = false
  }
}

const submitAnswer = async () => {
  if (!selectedAnswer.value || !currentQuestion.value) return
  isSubmitting.value = true
  try {
    const result = await submitReviewAnswer(currentQuestion.value.question_id, selectedAnswer.value)
    currentResult.value = result
    showResult.value = true
    if (result.is_correct) correctCount.value += 1
    if (result.is_correct) {
      if (result.removed_from_wrong) {
        ElMessage.success('答对，已移出错题本')
      } else if (result.remaining_to_remove > 0) {
        ElMessage.success(`答对，还需再答对 ${result.remaining_to_remove} 次`)
      } else {
        ElMessage.success('答对')
      }
    } else {
      ElMessage.warning('答错，留在错题本')
    }
    saveSession()
  } catch (error) {
    ElMessage.error(`提交失败：${error.response?.data?.detail || error.message}`)
  } finally {
    isSubmitting.value = false
  }
}

const nextQuestion = () => {
  if (currentIndex.value < reviewQuestions.value.length - 1) {
    currentIndex.value += 1
    selectedAnswer.value = ''
    showResult.value = false
    currentResult.value = null
  } else {
    reviewFinished.value = true
    clearSession()
    return
  }
  saveSession()
}

const restartReview = () => {
  clearSession()
  reviewStarted.value = false
  reviewFinished.value = false
  reviewQuestions.value = []
  currentIndex.value = 0
  selectedAnswer.value = ''
  showResult.value = false
  currentResult.value = null
  correctCount.value = 0
}

watch([selectedAnswer, currentIndex, showResult], saveSession)

onMounted(() => {
  const queryCount = Number(route.query.count)
  if (queryCount) reviewCount.value = queryCount
  const querySubjectId = Number(route.query.subject_id)
  subjectId.value = querySubjectId || null
  if (route.query.fresh) {
    clearSession()
    startReview()
    return
  }
  restoreSession()
})
</script>

<style scoped>
.review-page {
  min-height: calc(100vh - 49px);
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
  max-width: 860px;
  margin: 20px auto;
  padding: 0 20px;
}

.start-card,
.summary-card,
.question-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 24px;
}

.start-card {
  display: grid;
  justify-items: center;
  gap: 22px;
}

.count-row {
  display: flex;
  align-items: center;
  gap: 14px;
}

.progress-text {
  text-align: center;
  margin: 12px 0 18px;
  color: #909399;
}

.question-content {
  padding: 18px;
  background: #fafafa;
  border-radius: 8px;
  font-size: 18px;
  line-height: 1.8;
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

.result-box {
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

.actions,
.summary-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.summary-card {
  text-align: center;
}

.summary-card h2 {
  margin: 0 0 20px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.summary-grid div {
  display: grid;
  gap: 6px;
}

.summary-grid strong {
  font-size: 34px;
  color: #303133;
}

.summary-grid span {
  color: #909399;
}
</style>
