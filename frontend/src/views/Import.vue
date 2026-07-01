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
        <div class="nav-item" :class="{ active: $route.path === '/review' }" @click="$router.push('/review')">
          <el-icon><Refresh /></el-icon>
          <span>复习模式</span>
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
      <div class="import-page">
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
            <h1>导入练习集</h1>
            <p>支持多种格式导入：Excel、CSV、JSON、TXT/MD、PDF、DOCX 以及图片 OCR</p>
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

          <div class="format-info">
            <el-card class="format-card">
              <template #header>
                <div class="format-header">
                  <el-icon><List /></el-icon>
                  <span>推荐：使用 Excel 模板导入</span>
                </div>
              </template>
              <p>点击下方按钮下载标准导入模板，按照模板格式填写题目后上传。</p>
              <el-button type="primary" :icon="Download" :loading="downloading" @click="handleDownloadTemplate">
                下载 Excel 模板
              </el-button>
            </el-card>
            
            <div class="format-options">
              <div class="format-item">
                <el-icon class="format-icon"><List /></el-icon>
                <div>
                  <strong>.xlsx / .xls</strong>
                  <span>Excel 文件，推荐使用模板</span>
                </div>
              </div>
              <div class="format-item">
                <el-icon class="format-icon"><Document /></el-icon>
                <div>
                  <strong>.csv</strong>
                  <span>CSV 表格文件</span>
                </div>
              </div>
              <div class="format-item">
                <el-icon class="format-icon"><Folder /></el-icon>
                <div>
                  <strong>.json</strong>
                  <span>JSON 结构化数据</span>
                </div>
              </div>
              <div class="format-item">
                <el-icon class="format-icon"><Document /></el-icon>
                <div>
                  <strong>.txt / .md</strong>
                  <span>纯文本或 Markdown</span>
                </div>
              </div>
              <div class="format-item">
                <el-icon class="format-icon"><Folder /></el-icon>
                <div>
                  <strong>.pdf / .docx / 图片</strong>
                  <span>自动提取文本，图片会尝试 OCR</span>
                </div>
              </div>
            </div>
          </div>

          <el-input
            v-model="exerciseText"
            type="textarea"
            :rows="15"
            resize="vertical"
            placeholder="直接粘贴题库文本（支持自动解析），或上传文件导入..."
          />

          <div class="actions">
            <el-upload
              :show-file-list="false"
              :auto-upload="false"
              :on-change="handleMultiFileUpload"
              :multiple="true"
              accept=".txt,.md,.xlsx,.xls,.csv,.json,.pdf,.docx,.png,.jpg,.jpeg,.bmp,.webp,.gif,.tif,.tiff"
            >
              <el-button :icon="UploadFilled" :loading="extracting">上传文件</el-button>
            </el-upload>
            <el-button type="primary" :icon="Upload" :loading="loading" @click="handleParse">解析预览</el-button>
            <el-button :loading="aiParsing" @click="handleAiParse">AI 兜底解析</el-button>
            <el-button type="success" :disabled="!parsedQuestions.length" :loading="saving" @click="saveParsedQuestions">保存预览题目</el-button>
            <el-button :icon="Delete" @click="clearText">清空</el-button>
          </div>

          <div v-if="parseErrors.length > 0" class="error-list">
            <el-alert
              type="warning"
              show-icon
              :closable="false"
              title="解析警告"
            />
            <ul>
              <li v-for="(error, index) in parseErrors" :key="index">
                <el-icon><Warning /></el-icon>
                {{ error }}
              </li>
            </ul>
          </div>

          <div v-if="parsedQuestions.length" class="preview-list">
            <div class="preview-header">
              <h2>解析预览</h2>
              <span class="preview-count">共 {{ parsedQuestions.length }} 题</span>
            </div>
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
                placeholder="解析（选填）"
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

        <ProfileModal
          v-model:visible="showProfileModal"
          :username="username"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Back, Delete, Document, Plus, Refresh, Setting, Star, Upload, UploadFilled, CircleClose, Menu, Download, List, Folder, Warning } from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import { useUser } from '../composables/useUser'
import { createSubject, downloadImportTemplate, getSubjects, importParsedQuestions, parseQuestions, parseQuestionsWithAi, parseUploadedFile, parseUploadedFileWithAi } from '../api'
import ProfileModal from '../components/ProfileModal.vue'

const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()
const { username, avatar, loadUserInfo } = useUser()
const showProfileModal = ref(false)
const subjects = ref([])
const subjectId = ref(null)
const newSubjectName = ref('')
const exerciseText = ref('')
const loading = ref(false)
const saving = ref(false)
const downloading = ref(false)
const subjectCreating = ref(false)
const extracting = ref(false)
const aiParsing = ref(false)
const result = ref(null)
const parsedQuestions = ref([])
const parseErrors = ref([])
const textExts = new Set(['.txt', '.md'])
const imageExts = new Set(['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff'])
const previewableAssetExts = new Set(['.pdf', ...imageExts])
const lastUploadedFile = ref(null)

const applyParsedQuestions = (questions = []) => {
  parsedQuestions.value = questions.map(question => ensureMultiChoiceOptions({
    ...question,
    options: { ...(question.options || {}) }
  }))
}

const tryAiFallback = async (text, sourceName = '文本导入') => {
  const aiResult = await parseQuestionsWithAi(text, sourceName)
  if (aiResult.errors?.length) {
    parseErrors.value = [...parseErrors.value, ...aiResult.errors]
  }
  if (aiResult.parsed_questions?.length) {
    applyParsedQuestions(aiResult.parsed_questions)
    ElMessage.success(`规则解析失败，已通过 AI 兜底解析 ${aiResult.parsed_questions.length} 道题目`)
    return true
  }
  return false
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

const buildUploadFailureMessage = (fileName, detail) => {
  const ext = getFileExt(fileName)
  if (!imageExts.has(ext)) {
    return `处理文件失败：${detail}`
  }
  if (String(detail || '').includes('Tesseract OCR')) {
    return `图片上传成功，但 OCR 解析失败：${detail}`
  }
  return `图片处理失败：${detail}`
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

const handleDownloadTemplate = async () => {
  downloading.value = true
  try {
    const blob = await downloadImportTemplate()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '题目导入模板.xlsx'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('模板下载成功')
  } catch (error) {
    ElMessage.error(`下载模板失败：${error.response?.data?.detail || error.message}`)
  } finally {
    downloading.value = false
  }
}

const handleParse = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请选择科目')
    return
  }
  loading.value = true
  parseErrors.value = []
  try {
    const questions = await parseQuestions(exerciseText.value)
    if (questions.length) {
      applyParsedQuestions(questions)
      return
    }
    parsedQuestions.value = []
    ElMessage.warning('未能解析出题目，可点击“AI 兜底解析”继续尝试')
  } catch (error) {
    ElMessage.error(`解析失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const handleMultiFileUpload = async (file) => {
  if (!subjectId.value) {
    ElMessage.warning('请先选择科目')
    return
  }
  extracting.value = true
  parseErrors.value = []
  lastUploadedFile.value = file.raw
  try {
    const result = await parseUploadedFile(file.raw)
    
    if (result.errors && result.errors.length > 0) {
      parseErrors.value = result.errors
    }
    
    if (result.parsed_questions && result.parsed_questions.length > 0) {
      applyParsedQuestions(result.parsed_questions)
      ElMessage.success(`成功解析 ${result.parsed_questions.length} 道题目`)
    } else {
      ElMessage.warning('未能从文件中解析出题目，可点击“AI 兜底解析”继续尝试')
    }
  } catch (error) {
    const detail = error.response?.data?.detail || error.message
    ElMessage.error(buildUploadFailureMessage(file.raw?.name || file.name, detail))
  } finally {
    extracting.value = false
  }
}

const handleAiParse = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请选择科目')
    return
  }

  const text = exerciseText.value.trim()
  if (!text && !lastUploadedFile.value) {
    ElMessage.warning('请先粘贴文本或上传文件')
    return
  }

  aiParsing.value = true
  parseErrors.value = []
  try {
    if (text) {
      const aiSucceeded = await tryAiFallback(text, '文本粘贴导入')
      if (!aiSucceeded) {
        parsedQuestions.value = []
        ElMessage.warning('AI 未能解析出题目，请调整内容后重试')
      }
      return
    }

    const result = await parseUploadedFileWithAi(lastUploadedFile.value)
    if (result.errors?.length) {
      parseErrors.value = result.errors
    }
    if (result.parsed_questions?.length) {
      applyParsedQuestions(result.parsed_questions)
      ElMessage.success(`AI 兜底解析成功，共 ${result.parsed_questions.length} 道题目`)
    } else {
      parsedQuestions.value = []
      ElMessage.warning('AI 未能解析出题目，请更换文件或检查内容')
    }
  } catch (error) {
    ElMessage.error(`AI 解析失败：${error.response?.data?.detail || error.message}`)
  } finally {
    aiParsing.value = false
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
    parseErrors.value = []
    await loadSubjects()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const clearText = () => {
  exerciseText.value = ''
  lastUploadedFile.value = null
  result.value = null
  parsedQuestions.value = []
  parseErrors.value = []
}

onMounted(async () => {
  await loadUserInfo()
  loadSubjects()
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
  max-width: 1000px;
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

.format-info {
  margin-bottom: 16px;
}

.format-card {
  margin-bottom: 16px;
}

.format-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.format-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}

.format-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: #f8fafc;
  border-radius: 8px;
}

.format-icon {
  font-size: 24px;
  color: #3b82f6;
}

.format-item div {
  display: flex;
  flex-direction: column;
}

.format-item strong {
  font-size: 14px;
  color: #334155;
}

.format-item span {
  font-size: 12px;
  color: #94a3b8;
}

.actions {
  display: flex;
  gap: 10px;
  margin: 16px 0;
  flex-wrap: wrap;
}

.error-list {
  background: #fffbeb;
  border: 1px solid #fef3c7;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.error-list ul {
  margin: 0;
  padding: 0 0 0 20px;
}

.error-list li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #d97706;
  font-size: 13px;
  margin-bottom: 4px;
}

.preview-list {
  display: grid;
  gap: 14px;
  margin-top: 18px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.preview-header h2 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.preview-count {
  font-size: 14px;
  color: #909399;
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
}</style>
