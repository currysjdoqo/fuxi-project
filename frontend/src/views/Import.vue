<template>
  <div class="import-page">
    <header class="page-header">
      <div>
        <h1>导入习题集</h1>
        <p>先选择科目，再粘贴题库文本导入。</p>
      </div>
      <el-button :icon="Back" @click="$router.push('/')">返回练习</el-button>
    </header>

    <section class="import-panel">
      <div class="subject-row">
        <el-select v-model="subjectId" placeholder="选择科目" filterable>
          <el-option
            v-for="subject in subjects"
            :key="subject.id"
            :label="`${subject.name}（${subject.question_count}题）`"
            :value="subject.id"
          />
        </el-select>
        <el-input v-model="newSubjectName" placeholder="新科目，例如：机器学习" @keyup.enter="handleCreateSubject" />
        <el-button :icon="Plus" :loading="subjectCreating" @click="handleCreateSubject">创建</el-button>
      </div>

      <el-input
        v-model="exerciseText"
        type="textarea"
        :rows="22"
        resize="vertical"
        placeholder="一.单选题（共10题,100.0分）
1
机器学习的目标是( )
A、让计算机存储更多数据
B、模拟和实现人类的学习功能
C、提高计算机的运算速度
D、替代人类进行所有工作
正确答案： B 我的答案：B得分： 10.0分
答案解析：
课件中明确指出..."
      />

      <div class="actions">
        <el-button type="primary" :icon="Upload" :loading="loading" @click="handleParse">解析预览</el-button>
        <el-button type="success" :disabled="!parsedQuestions.length" :loading="saving" @click="saveParsedQuestions">保存预览题目</el-button>
        <el-button :icon="Delete" @click="clearText">清空</el-button>
      </div>

      <div v-if="parsedQuestions.length" class="preview-list">
        <h2>解析预览</h2>
        <div v-for="(question, index) in parsedQuestions" :key="index" class="preview-item">
          <div class="preview-head">
            <strong>第 {{ index + 1 }} 题</strong>
            <el-select v-model="question.type" class="type-select">
              <el-option label="单选题" value="single" />
              <el-option label="多选题" value="multi" />
              <el-option label="判断题" value="judge" />
              <el-option label="填空题" value="fill" />
              <el-option label="简答题" value="short" />
              <el-option label="编程题" value="code" />
            </el-select>
          </div>
          <el-input v-model="question.content" type="textarea" :rows="2" placeholder="题干" />
          <div v-if="question.type === 'single'" class="option-grid">
            <el-input v-for="key in ['A', 'B', 'C', 'D']" :key="key" v-model="question.options[key]" :placeholder="`选项 ${key}`" />
          </div>
          <div v-else-if="question.type === 'multi'" class="option-grid">
            <el-input v-for="key in ['A', 'B', 'C', 'D', 'E', 'F']" :key="key" v-model="question.options[key]" :placeholder="`选项 ${key}`" />
          </div>
          <div v-if="question.type === 'judge'" class="option-grid">
            <el-input v-model="question.options.T" placeholder="正确显示文本" />
            <el-input v-model="question.options.F" placeholder="错误显示文本" />
          </div>
          <el-input
            v-model="question.answer"
            :type="question.type === 'code' ? 'textarea' : 'text'"
            :rows="question.type === 'code' ? 5 : 1"
            placeholder="答案。判断题请填 T/F；简答题和编程题可留空"
          />
          <el-input v-model="question.explanation" type="textarea" :rows="2" placeholder="解析" />
        </div>
      </div>

      <el-alert
        v-if="result"
        type="success"
        show-icon
        :closable="false"
        :title="`导入完成：解析 ${result.parsed_count} 题，成功新增 ${result.inserted_count} 题，跳过重复 ${result.parsed_count - result.inserted_count} 题。`"
      />
    </section>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Back, Delete, Plus, Upload } from '@element-plus/icons-vue'
import { createSubject, getSubjects, importParsedQuestions, parseQuestions } from '../api'

const subjects = ref([])
const subjectId = ref(null)
const newSubjectName = ref('')
const exerciseText = ref('')
const loading = ref(false)
const saving = ref(false)
const subjectCreating = ref(false)
const result = ref(null)
const parsedQuestions = ref([])

const ensureMultiChoiceOptions = (question) => {
  if (question.type === 'multi' && (!question.options || !Object.keys(question.options).length)) {
    question.options = { A: '', B: '', C: '', D: '', E: '', F: '' }
  }
  if (question.type === 'single' && (!question.options || !Object.keys(question.options).length)) {
    question.options = { A: '', B: '', C: '', D: '' }
  }
  if (question.type === 'judge' && (!question.options || !Object.keys(question.options).length)) {
    question.options = { T: '正确', F: '错误' }
  }
  return question
}

const loadSubjects = async () => {
  try {
    subjects.value = await getSubjects()
    if (!subjectId.value && subjects.value.length) {
      subjectId.value = subjects.value[0].id
    }
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
    subjectId.value = subject.id
    ElMessage.success('科目已创建')
  } catch (error) {
    ElMessage.error(`创建科目失败：${error.response?.data?.detail || error.message}`)
  } finally {
    subjectCreating.value = false
  }
}

const handleParse = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请先选择或创建科目')
    return
  }
  if (!exerciseText.value.trim()) {
    ElMessage.warning('请先粘贴习题文本')
    return
  }

  loading.value = true
  result.value = null
  try {
    parsedQuestions.value = await parseQuestions(exerciseText.value)
    parsedQuestions.value = parsedQuestions.value.map(ensureMultiChoiceOptions)
    if (!parsedQuestions.value.length) {
      ElMessage.warning('没有解析到题目，请检查文本格式')
      return
    }
    ElMessage.success(`解析出 ${parsedQuestions.value.length} 题，请检查并可修改答案后保存`)
  } catch (error) {
    ElMessage.error(`解析失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const saveParsedQuestions = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请先选择或创建科目')
    return
  }
  const invalid = parsedQuestions.value.find((question) => {
    if (!question.content.trim()) return true
    if (['short', 'code'].includes(question.type)) return false
    return !question.answer.trim()
  })
  if (invalid) {
    ElMessage.warning('题干不能为空；除简答题/编程题外，答案不能为空')
    return
  }

  saving.value = true
  result.value = null
  try {
    parsedQuestions.value = parsedQuestions.value.map(ensureMultiChoiceOptions)
    result.value = await importParsedQuestions(parsedQuestions.value, subjectId.value)
    ElMessage.success(`保存成功，新增 ${result.value.inserted_count} 题`)
    parsedQuestions.value = []
    await loadSubjects()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const clearText = () => {
  exerciseText.value = ''
  result.value = null
  parsedQuestions.value = []
}

onMounted(loadSubjects)
</script>

<style scoped>
.import-page {
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

.import-panel {
  max-width: 980px;
  margin: 20px auto;
  padding: 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.subject-row {
  display: grid;
  grid-template-columns: 260px 1fr auto;
  gap: 10px;
  margin-bottom: 16px;
}

.actions {
  display: flex;
  gap: 10px;
  margin: 16px 0;
}

.preview-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.preview-list h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.preview-item {
  display: grid;
  gap: 10px;
  padding: 14px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background: #fafafa;
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-select {
  width: 140px;
}

.option-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (max-width: 760px) {
  .subject-row {
    grid-template-columns: 1fr;
  }
}
</style>
