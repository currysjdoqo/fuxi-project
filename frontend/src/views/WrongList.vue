<template>
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
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Collection, Delete, Edit, Refresh } from '@element-plus/icons-vue'
import { getSubjects, getWrongQuestions, removeWrongQuestion } from '../api'

const route = useRoute()
const router = useRouter()
const subjects = ref([])
const selectedSubjectId = ref(null)
const wrongList = ref([])
const loading = ref(false)
const reviewDialogVisible = ref(false)
const reviewCount = ref(10)

const selectedSubject = computed(() => subjects.value.find((subject) => subject.id === selectedSubjectId.value))

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

const loadSubjects = async () => {
  subjects.value = await getSubjects()
  const querySubjectId = Number(route.query.subject_id)
  const preferred = subjects.value.find((subject) => subject.id === querySubjectId)
  const firstWrongBook = subjects.value.find((subject) => subject.wrong_count > 0)
  if (!selectedSubjectId.value) {
    selectedSubjectId.value = preferred?.id || firstWrongBook?.id || subjects.value[0]?.id || null
  }
}

const loadWrongQuestions = async () => {
  if (!selectedSubjectId.value) {
    wrongList.value = []
    return
  }

  loading.value = true
  try {
    wrongList.value = await getWrongQuestions(selectedSubjectId.value)
  } catch (error) {
    ElMessage.error(`加载错题失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const refreshAll = async () => {
  try {
    await loadSubjects()
    await loadWrongQuestions()
  } catch (error) {
    ElMessage.error(`刷新失败：${error.response?.data?.detail || error.message}`)
  }
}

const selectSubject = async (subject) => {
  selectedSubjectId.value = subject.id
  router.replace({ path: '/wrong', query: { subject_id: subject.id } })
  await loadWrongQuestions()
}

const redoQuestion = (row) => {
  router.push({ path: '/', query: { subject_id: row.subject_id, question_id: row.question_id } })
}

const openReviewDialog = () => {
  if (!selectedSubject.value) {
    ElMessage.info('请先选择错题本')
    return
  }
  if (!wrongList.value.length) {
    ElMessage.info('当前错题本为空')
    return
  }
  reviewCount.value = Math.min(10, wrongList.value.length)
  reviewDialogVisible.value = true
}

const startReview = () => {
  reviewDialogVisible.value = false
  router.push({
    path: '/review',
    query: {
      subject_id: selectedSubjectId.value,
      count: reviewCount.value,
      fresh: Date.now()
    }
  })
}

const removeQuestion = async (questionId) => {
  try {
    await ElMessageBox.confirm('确认从当前错题本移除这道题？', '移除错题', { type: 'warning' })
    await removeWrongQuestion(questionId)
    ElMessage.success('已移除')
    await refreshAll()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`移除失败：${error.response?.data?.detail || error.message}`)
    }
  }
}

onMounted(refreshAll)
</script>

<style scoped>
.wrong-page {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.book-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 14px;
  padding: 20px 20px 0;
}

.book-card {
  min-height: 106px;
  display: grid;
  align-content: center;
  gap: 6px;
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fff;
  text-align: left;
  cursor: pointer;
}

.book-card:hover,
.book-card.active {
  border-color: #409eff;
  background: #f5f9ff;
}

.book-card.empty {
  opacity: 0.68;
}

.book-card strong {
  font-size: 17px;
  color: #303133;
}

.book-card span {
  color: #f56c6c;
  font-weight: 600;
}

.book-card small {
  color: #909399;
}

.table-panel {
  padding: 20px;
}

.stem,
.explanation {
  white-space: pre-wrap;
  line-height: 1.6;
  color: #606266;
}

.dialog-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
</style>
