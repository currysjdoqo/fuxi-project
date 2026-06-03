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
      <div class="import-page">
        <header class="page-header">
          <div>
            <h1>导入练习集</h1>
            <p>先选择科目，再粘贴题库文本或上传附件导入。</p>
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
            placeholder="直接粘贴题库文本。TXT / MD 会走文本解析；PDF、Word、图片、压缩包等会作为附件题导入。"
          />

          <div class="actions">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              :on-change="handleFileUpload"
              accept=".txt,.md,.pdf,.docx,.png,.jpg,.jpeg,.bmp,.webp,.zip,.ppt,.pptx,.xls,.xlsx,.csv,.json,.xml,.mp3,.mp4,.avi,.mov,.mkv"
            >
              <el-button :icon="UploadFilled" :loading="extracting">上传文件</el-button>
            </el-upload>
            <el-upload
              :file-list="uploadedFiles"
              :on-change="handleUploadedFilesChange"
              :on-remove="handleUploadedFilesChange"
              :auto-upload="false"
              :multiple="true"
              accept=".txt,.md,.pdf,.docx,.png,.jpg,.jpeg,.bmp,.webp,.zip,.ppt,.pptx,.xls,.xlsx,.csv,.json,.xml,.mp3,.mp4,.avi,.mov,.mkv"
            >
              <el-button :icon="UploadFilled">选择文件</el-button>
            </el-upload>
            <el-button type="primary" :icon="Upload" :loading="extracting" :disabled="!uploadedFiles.length" @click="uploadSelectedFiles">处理文件</el-button>
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

              <div v-if="question.type === 'code' && question.options._asset_url" class="attachment-box">
                <el-tag type="info">附件：{{ question.options._asset_name }}</el-tag>
                <el-tag v-if="!question.options._asset_previewable" type="warning">不可预览，直接打开或下载</el-tag>
                <span>{{ question.options._asset_url }}</span>
              </div>

              <div v-else-if="question.type === 'single'" class="option-grid">
                <el-input v-for="key in ['A', 'B', 'C', 'D']" :key="key" v-model="question.options[key]" :placeholder="`选项 ${key}`" />
              </div>

              <div v-else-if="question.type === 'multi'" class="option-grid">
                <el-input v-for="key in ['A', 'B', 'C', 'D', 'E', 'F']" :key="key" v-model="question.options[key]" :placeholder="`选项 ${key}`" />
              </div>

              <div v-if="question.type === 'judge'" class="option-grid">
                <el-input v-model="question.options.T" placeholder="正确时显示的文字" />
                <el-input v-model="question.options.F" placeholder="错误时显示的文字" />
              </div>

              <el-input
                v-model="question.answer"
                :type="question.type === 'code' ? 'textarea' : 'text'"
                :rows="question.type === 'code' ? 5 : 1"
                :disabled="question.type === 'code' && question.options._asset_url"
                placeholder="答案。判断题请填 T/F；简答题和附件编程题可留空"
              />

              <el-input
                v-model="question.explanation"
                type="textarea"
                :rows="2"
                :disabled="question.type === 'code' && question.options._asset_url"
                placeholder="解析"
              />
            </div>
          </div>

          <el-alert
            v-if="result"
            type="success"
            show-icon
            :closable="false"
            :title="'导入完成：解析 ' + result.parsed_count + ' 题，新增 ' + result.inserted_count + ' 题，跳过重复 ' + (result.parsed_count - result.inserted_count) + ' 题'"
          />
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Delete, Document, Plus, Refresh, Setting, Star, Upload, UploadFilled, CircleClose } from '@element-plus/icons-vue'
import { createSubject, extractTextFromFile, extractMultipleFiles, getSubjects, importParsedQuestions, parseQuestions } from '../api'

const router = useRouter()
const username = ref(localStorage.getItem('auth_username') || '用户')
const subjects = ref([])
const subjectId = ref(null)
const newSubjectName = ref('')
const exerciseText = ref('')
const loading = ref(false)
const saving = ref(false)
const subjectCreating = ref(false)
const extracting = ref(false)
const result = ref(null)
const parsedQuestions = ref([])
const uploadedFiles = ref([])
const textExts = new Set(['.txt', '.md'])
const previewableAssetExts = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.bmp', '.webp'])

const handleUploadedFilesChange = (_file, fileList) => {
  uploadedFiles.value = fileList
}

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem('auth_session_ok')
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const getFileExt = (name = '') => {
  const index = name.lastIndexOf('.')
  return index >= 0 ? name.slice(index).toLowerCase() : ''
}

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
    ElMessage.warning('请选择科目')
    return
  }
  loading.value = true
  try {
    parsedQuestions.value = await parseQuestions(exerciseText.value)
    if (!parsedQuestions.value.length) {
      ElMessage.warning('未能解析出题目')
    }
  } catch (error) {
    ElMessage.error(`解析失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const handleFileUpload = async (file) => {
  // 单个文件上传，仅作为兼容保留
  if (!subjectId.value) {
    ElMessage.warning('请先选择科目')
    return
  }
  extracting.value = true
  try {
    const ext = getFileExt(file.name)
    if (textExts.has(ext)) {
      const reader = new FileReader()
      reader.onload = async () => {
        try {
          exerciseText.value = String(reader.result)
          ElMessage.success('文件读取成功，请点击「解析预览」')
        } catch (e) {
          ElMessage.error(`读取文件失败：${e}`)
        } finally {
          extracting.value = false
        }
      }
      reader.readAsText(file.raw)
    } else {
      const previewable = previewableAssetExts.has(ext)
      const { asset_url, filename, asset_download_url } = await extractTextFromFile(file.raw)
      parsedQuestions.value = [
        {
          type: 'code',
          content: filename || file.name,
          options: { _asset_url: asset_url, _asset_download_url: asset_download_url || asset_url, _asset_name: filename || file.name, _asset_previewable: previewable },
          answer: '',
          explanation: ''
        }
      ]
      ElMessage.success('文件上传成功，已转为附件编程题，请点击「保存预览题目」')
    }
  } catch (error) {
    ElMessage.error(`处理文件失败：${error.response?.data?.detail || error.message}`)
  } finally {
    extracting.value = false
  }
}

const uploadSelectedFiles = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请先选择科目')
    return
  }
  if (!uploadedFiles.value || !uploadedFiles.value.length) {
    ElMessage.warning('请先选择文件')
    return
  }
  extracting.value = true
  try {
    const files = uploadedFiles.value.map(f => f.raw)
    const result = await extractMultipleFiles(files)
    let newQuestions = []
    
    // 处理文本文件的解析
    if (result.parsed_questions && result.parsed_questions.length > 0) {
      newQuestions = newQuestions.concat(result.parsed_questions)
    }
    
    // 处理附件文件
    if (result.assets && result.assets.length > 0) {
      for (const asset of result.assets) {
        const ext = '.' + asset.asset_saved_name.split('.').pop().toLowerCase()
        const previewable = previewableAssetExts.has(ext)
        newQuestions.push({
          type: 'code',
          content: asset.filename,
          options: { 
            _asset_url: asset.asset_url, 
            _asset_download_url: asset.asset_download_url, 
            _asset_name: asset.filename, 
            _asset_previewable: previewable 
          },
          answer: '',
          explanation: ''
        })
      }
    }
    
    // 合并文本内容
    if (result.text_contents) {
      exerciseText.value = result.text_contents
    }
    
    if (newQuestions.length > 0) {
      parsedQuestions.value = newQuestions
      ElMessage.success(`成功处理 ${result.processed_files} 个文件，解析出 ${newQuestions.length} 道题目`)
    } else {
      ElMessage.success(`成功处理 ${result.processed_files} 个文件`)
    }
    // 清空文件列表
    uploadedFiles.value = []
  } catch (error) {
    ElMessage.error(`处理文件失败：${error.response?.data?.detail || error.message}`)
  } finally {
    extracting.value = false
  }
}

const isAttachmentCodeQuestion = (question) => {
  return question.type === 'code' && (question.options._asset_url || Object.keys(question.options).some(k => k.startsWith('_')))
}

const saveParsedQuestions = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请选择科目')
    return
  }
  if (!parsedQuestions.value.length) {
    ElMessage.warning('请先解析题目')
    return
  }

  const invalid = parsedQuestions.value.find((question) => {
    if (!question.content.trim()) return true
    if (isAttachmentCodeQuestion(question)) return false
    if (['short', 'code'].includes(question.type)) return false
    return !question.answer.trim()
  })

  if (invalid) {
    ElMessage.warning('题干不能为空；除简答题和附件编程题外，答案不能为空')
    return
  }

  saving.value = true
  result.value = null
  try {
    parsedQuestions.value = parsedQuestions.value.map(ensureMultiChoiceOptions)
    result.value = await importParsedQuestions(parsedQuestions.value, subjectId.value)
    ElMessage.success(`保存成功，新增加 ${result.value.inserted_count} 题`)
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
  uploadedFiles.value = []
}

onMounted(loadSubjects)
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

.import-page {
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
  flex-wrap: wrap;
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
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.type-select {
  width: 120px;
}

.option-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.attachment-box {
  display: flex;
  gap: 10px;
  align-items: center;
}
</style>
