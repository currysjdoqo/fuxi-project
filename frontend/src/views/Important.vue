<template>
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
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getQuestions, getSubjects, updateQuestionImportant } from '../api'

const router = useRouter()
const subjects = ref([])
const subjectId = ref(null)
const importantList = ref([])
const loading = ref(false)

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
.important-page {
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
