<template>
  <Layout :username="username" :avatar="avatar" @show-profile="showProfileModal = true" @logout="handleLogout">
    <div class="import-page">
        <header class="page-header">
          <div>
            <h1>导入练习集</h1>
            <p>支持多种格式导入：Excel、CSV、JSON、TXT/MD、PDF、DOCX 以及图片 OCR</p>
          </div>
          <el-button :icon="Back" @click="$router.push('/')">返回练习</el-button>
        </header>

        <section class="import-panel">
          <div class="subject-row">
            <el-select v-model="subjectId" placeholder="选择科目" filterable @change="handleSubjectChange">
              <el-option-group
                v-for="group in folderGroups"
                :key="group.id"
                :label="group.name + `（${group.subject_count}个）`"
              >
                <el-option
                  v-for="subject in group.subjects"
                  :key="subject.id"
                  :label="`${subject.name}（${subject.question_count}题）`"
                  :value="subject.id"
                />
              </el-option-group>
            </el-select>
            <el-input v-model="newSubjectName" placeholder="新科目，例如：机器学习" style="width: 160px" @keyup.enter="handleCreateSubject" />
            <el-select v-model="newSubjectFolderId" placeholder="归入文件夹" clearable style="width: 140px">
              <el-option
                v-for="group in folderGroups.filter(f => f.id !== -1)"
                :key="group.id"
                :label="group.name"
                :value="group.id"
              />
            </el-select>
            <el-button :icon="Plus" :loading="subjectCreating" @click="handleCreateSubject">创建</el-button>
          </div>

          <div class="subject-row chapter-row">
            <el-select
              v-model="defaultChapterName"
              placeholder="本批题目归入章节（选填，可分章节导入）"
              clearable
              filterable
              @change="handleDefaultChapterChange"
            >
              <el-option
                v-for="chapter in chapters"
                :key="chapter.id"
                :label="chapter.name"
                :value="chapter.name"
              />
            </el-select>
            <el-input v-model="newChapterName" placeholder="新章节，例如：第1章 绪论" @keyup.enter="handleCreateChapter" />
            <el-button :icon="Plus" :loading="chapterCreating" @click="handleCreateChapter">创建章节</el-button>
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
            <el-button
              v-if="smartStats && smartStats.remaining_residual_count"
              type="warning"
              plain
              :loading="completingResiduals"
              @click="handleCompleteResiduals"
            >AI 补全残块</el-button>
            <el-button :loading="aiParsing" @click="handleAiParse">AI 兜底解析</el-button>
            <el-button
              type="warning"
              plain
              :disabled="!parsedQuestions.length"
              :loading="chapterAssigning"
              @click="handleAiAssignChapters"
            >AI 划分章节</el-button>
            <el-button type="success" :disabled="!parsedQuestions.length" :loading="saving" @click="saveParsedQuestions">保存预览题目</el-button>
            <el-button :icon="Delete" @click="clearText">清空</el-button>
          </div>

          <div v-if="smartStats" class="smart-stats">
            <el-tag size="small" type="info">规则识别 {{ smartStats.rule_count ?? 0 }} 题</el-tag>
            <el-tag v-if="smartStats.ai_added_questions ?? smartStats.ai_added" size="small" type="warning">AI 补全 {{ smartStats.ai_added_questions ?? smartStats.ai_added }} 题</el-tag>
            <el-tag v-if="smartStats.cache_hit" size="small" type="success">命中缓存</el-tag>
            <el-tag v-if="smartStats.remaining_residual_count" size="small" type="danger">
              剩余 {{ smartStats.remaining_residual_count }} 段未识别
            </el-tag>
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
                <div class="preview-head-controls">
                  <el-select
                    v-model="question.chapter_name"
                    class="chapter-select"
                    filterable
                    allow-create
                    default-first-option
                    clearable
                    placeholder="未分章（可选择或输入章节）"
                  >
                    <el-option label="未分章" value="" />
                    <el-option
                      v-for="name in chapterNameOptions"
                      :key="name"
                      :label="name"
                      :value="name"
                    />
                  </el-select>
                  <el-select v-model="question.type" class="type-select">
                    <el-option label="单选题" value="single" />
                    <el-option label="多选题" value="multi" />
                    <el-option label="判断题" value="judge" />
                    <el-option label="填空题" value="fill" />
                    <el-option label="简答题" value="short" />
                    <el-option label="编程题" value="code" />
                  </el-select>
                </div>
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
</Layout>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Back, Delete, Document, Plus, Refresh, Setting, Star, Upload, UploadFilled, CircleClose, Menu, Download, List, Folder, Warning } from '@element-plus/icons-vue'
import { useUser } from '../composables/useUser'
import { clearAuthSession } from '../utils/authStorage'
import { ElMessageBox } from 'element-plus'
import { aiAssignChapters, createChapter, createSubject, downloadImportTemplate, getChapters, getSubjects, importParsedQuestions, smartParseFile, smartParseText } from '../api'
import ProfileModal from '../components/ProfileModal.vue'
import Layout from '../components/Layout/Layout.vue'

const router = useRouter()
const { username, avatar, loadUserInfo } = useUser()
const showProfileModal = ref(false)
const subjects = ref([])
const folderGroups = ref([])
const subjectId = ref(null)
const newSubjectName = ref('')
const newSubjectFolderId = ref(null)
const chapters = ref([])
const defaultChapterName = ref('')
const newChapterName = ref('')
const chapterCreating = ref(false)
const chapterAssigning = ref(false)
const exerciseText = ref('')
const loading = ref(false)
const saving = ref(false)
const downloading = ref(false)
const subjectCreating = ref(false)
const extracting = ref(false)
const aiParsing = ref(false)
const completingResiduals = ref(false)
const smartStats = ref(null)
const lastSource = ref({ kind: 'text' })
const result = ref(null)
const parsedQuestions = ref([])
const parseErrors = ref([])
const textExts = new Set(['.txt', '.md'])
const imageExts = new Set(['.png', '.jpg', '.jpeg', '.bmp', '.webp', '.gif', '.tif', '.tiff'])
const previewableAssetExts = new Set(['.pdf', ...imageExts])
const lastUploadedFile = ref(null)

const chapterNameOptions = computed(() => {
  const names = chapters.value.map(chapter => chapter.name)
  parsedQuestions.value.forEach((question) => {
    const name = (question.chapter_name || '').trim()
    if (name && !names.includes(name)) {
      names.push(name)
    }
  })
  if (defaultChapterName.value && !names.includes(defaultChapterName.value)) {
    names.push(defaultChapterName.value)
  }
  return names
})

const applyParsedQuestions = (questions = []) => {
  parsedQuestions.value = questions.map(question => ensureMultiChoiceOptions({
    ...question,
    options: { ...(question.options || {}) },
    chapter_name: question.chapter_name || defaultChapterName.value || ''
  }))
}

const describeSmartStats = (stats = {}) => {
  const parts = [`规则识别 ${(stats.rule_count ?? 0)} 题`]
  if (stats.ai_added_questions ?? stats.ai_added) {
    parts.push(`AI 补全 ${stats.ai_added_questions ?? stats.ai_added} 题`)
  }
  if (stats.cache_hit) {
    parts.push('命中缓存')
  }
  if (stats.remaining_residual_count) {
    parts.push(`仍剩 ${stats.remaining_residual_count} 段未识别`)
  }
  return parts.join(' · ')
}

const applySmartResult = (parsed, { successText = '' } = {}) => {
  const stats = parsed.stats || {}
  smartStats.value = stats
  if (parsed.errors?.length) {
    parseErrors.value = [...parseErrors.value, ...parsed.errors]
  }
  if (parsed.questions?.length) {
    applyParsedQuestions(parsed.questions)
    const message = successText || `已识别 ${parsed.questions.length} 道题目（${describeSmartStats(stats)}）`
    ElMessage.success(message)
    return true
  }
  parsedQuestions.value = []
  return false
}

const tryAiFallback = async (text, sourceName = '文本导入') => {
  const parsed = await smartParseText(text, { sourceName, aiFallback: true, forceResiduals: true })
  return applySmartResult(parsed, {
    successText: `AI 兜底解析完成，共 ${parsed.questions?.length || 0} 道题目`
  })
}

const handleLogout = () => {
  clearAuthSession()
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
    folderGroups.value = await getFoldersWithSubjects()
    subjects.value = folderGroups.value.flatMap(g => g.subjects || [])
    if (!subjectId.value && subjects.value.length) {
      subjectId.value = subjects.value[0].id
    }
    await loadChapters()
  } catch (error) {
    ElMessage.error(`加载科目失败：${error.response?.data?.detail || error.message}`)
  }
}

const loadChapters = async () => {
  if (!subjectId.value) {
    chapters.value = []
    return
  }
  try {
    chapters.value = await getChapters(subjectId.value)
  } catch (error) {
    chapters.value = []
  }
}

const handleSubjectChange = async () => {
  defaultChapterName.value = ''
  newChapterName.value = ''
  await loadChapters()
}

const handleDefaultChapterChange = () => {
  if (!defaultChapterName.value) return
  parsedQuestions.value.forEach((question) => {
    if (!question.chapter_name) {
      question.chapter_name = defaultChapterName.value
    }
  })
}

const handleCreateChapter = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请先选择科目')
    return
  }
  const name = newChapterName.value.trim()
  if (!name) {
    ElMessage.warning('请输入章节名称')
    return
  }
  chapterCreating.value = true
  try {
    const chapter = await createChapter(subjectId.value, name)
    newChapterName.value = ''
    await loadChapters()
    defaultChapterName.value = chapter.name
    handleDefaultChapterChange()
    ElMessage.success(`章节「${name}」已创建，已应用到未分章的题目`)
  } catch (error) {
    ElMessage.error(`创建章节失败：${error.response?.data?.detail || error.message}`)
  } finally {
    chapterCreating.value = false
  }
}

const handleCreateSubject = async () => {
  if (!newSubjectName.value.trim()) {
    ElMessage.warning('请输入科目名称')
    return
  }
  subjectCreating.value = true
  try {
    const subject = await createSubject(newSubjectName.value.trim(), newSubjectFolderId.value)
    newSubjectName.value = ''
    newSubjectFolderId.value = null
    await loadSubjects()
    subjectId.value = subject.id
    await handleSubjectChange()
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
    lastSource.value = { kind: 'text' }
    const parsed = await smartParseText(exerciseText.value, { sourceName: '题目粘贴导入', aiFallback: false })
    if (!applySmartResult(parsed)) {
      ElMessage.warning('未能解析出题目，可点击“AI 兜底解析”继续尝试')
      return
    }
    if (parsed.stats?.remaining_residual_count) {
      ElMessage.warning(`还有 ${parsed.stats.remaining_residual_count} 段内容未能识别，可点击“AI 补全残块”`)
    }
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
  lastSource.value = { kind: 'file', file: file.raw }
  try {
    const parsed = await smartParseFile(file.raw, { aiFallback: false })

    if (!applySmartResult(parsed)) {
      ElMessage.warning('未能从文件中解析出题目，可点击“AI 兜底解析”继续尝试')
      return
    }
    if (parsed.stats?.remaining_residual_count) {
      ElMessage.warning(`还有 ${parsed.stats.remaining_residual_count} 段内容未能识别，可点击“AI 补全残块”`)
    }
  } catch (error) {
    const detail = error.response?.data?.detail || error.message
    ElMessage.error(buildUploadFailureMessage(file.raw?.name || file.name, detail))
  } finally {
    extracting.value = false
  }
}

const handleCompleteResiduals = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请选择科目')
    return
  }
  const residualCount = smartStats.value?.remaining_residual_count || 0
  if (residualCount > 20) {
    const estimated = smartStats.value?.estimated_ai_questions || residualCount
    try {
      await ElMessageBox.confirm(
        `还有 ${residualCount} 段残块，预计需要 AI 补全 ${estimated} 题，可能产生 API 费用。是否继续？`,
        '确认 AI 补全',
        { type: 'warning', confirmButtonText: '继续补全', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
  }
  completingResiduals.value = true
  parseErrors.value = []
  try {
    const source = lastSource.value || { kind: 'text' }
    const parsed = source.kind === 'file' && source.file
      ? await smartParseFile(source.file, { aiFallback: true, forceResiduals: true })
      : await smartParseText(exerciseText.value, { sourceName: '题目粘贴导入', aiFallback: true, forceResiduals: true })

    if (applySmartResult(parsed, { successText: `AI 补全完成，共 ${parsed.questions?.length || 0} 道题目（${describeSmartStats(parsed.stats || {})}）` })) {
      return
    }
    ElMessage.warning('AI 未能补全剩余内容')
  } catch (error) {
    ElMessage.error(`AI 补全失败：${error.response?.data?.detail || error.message}`)
  } finally {
    completingResiduals.value = false
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
      lastSource.value = { kind: 'text' }
      const parsed = await smartParseText(text, { sourceName: '文本粘贴导入', aiFallback: true })
      if (applySmartResult(parsed, { successText: `AI 解析成功，共 ${parsed.questions?.length || 0} 道题目（${describeSmartStats(parsed.stats || {})}）` })) {
        return
      }
      // 规则完全没定位到题目时，退化为整段送 AI（可能产生费用，由用户主动点击触发）
      const aiSucceeded = await tryAiFallback(text, '文本粘贴导入')
      if (!aiSucceeded) {
        parsedQuestions.value = []
        ElMessage.warning('AI 未能解析出题目，请调整内容后重试')
      }
      return
    }

    lastSource.value = { kind: 'file', file: lastUploadedFile.value }
    const parsedFile = await smartParseFile(lastUploadedFile.value, { aiFallback: true })
    if (applySmartResult(parsedFile, { successText: `AI 解析成功，共 ${parsedFile.questions?.length || 0} 道题目（${describeSmartStats(parsedFile.stats || {})}）` })) {
      return
    }

    const fallback = await smartParseFile(lastUploadedFile.value, { aiFallback: true, forceResiduals: true })
    if (!applySmartResult(fallback, { successText: `AI 兜底解析完成，共 ${fallback.questions?.length || 0} 道题目` })) {
      parsedQuestions.value = []
      ElMessage.warning('AI 未能解析出题目，请更换文件或检查内容')
    }
  } catch (error) {
    ElMessage.error(`AI 解析失败：${error.response?.data?.detail || error.message}`)
  } finally {
    aiParsing.value = false
  }
}

const handleAiAssignChapters = async () => {
  if (!subjectId.value) {
    ElMessage.warning('请选择科目')
    return
  }
  if (!parsedQuestions.value.length) {
    ElMessage.warning('请先解析题目')
    return
  }

  chapterAssigning.value = true
  parseErrors.value = []
  try {
    const result = await aiAssignChapters(subjectId.value, parsedQuestions.value)
    if (result.errors?.length) {
      parseErrors.value = result.errors
    }
    if (result.assignments?.length) {
      const assignmentMap = {}
      result.assignments.forEach((item) => {
        assignmentMap[item.index] = item.chapter
      })
      let applied = 0
      parsedQuestions.value.forEach((question, index) => {
        if (assignmentMap[index]) {
          question.chapter_name = assignmentMap[index]
          applied++
        }
      })
      // 收集 AI 生成的新章节名，刷新下拉
      const aiChapters = [...new Set(result.assignments.map((a) => a.chapter))]
      const existing = new Set(chapters.value.map((c) => c.name))
      aiChapters.forEach((name) => {
        if (!existing.has(name)) {
          chapters.value.push({ id: 0, name, question_count: 0 })
        }
      })
      ElMessage.success(`AI 已为 ${applied} 道题目划分章节，可在预览中逐题调整`)
    } else {
      ElMessage.warning('AI 未能划分章节，请检查 API Key 配置后重试')
    }
  } catch (error) {
    ElMessage.error(`AI 划分章节失败：${error.response?.data?.detail || error.message}`)
  } finally {
    chapterAssigning.value = false
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
    await loadChapters()
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
  smartStats.value = null
  lastSource.value = { kind: 'text' }
}

onMounted(async () => {
  await loadUserInfo()
  loadSubjects()
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

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-section .logo-icon {
  width: 40px;
  height: 40px;
  color: #b85c38;
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
  color: #a89985;
  cursor: pointer;
  transition: color 0.2s ease;
}

.logout-btn:hover {
  color: #e8dfd0;
}

.main-content {
  flex: 1;
  position: relative;
  min-width: 0;
  min-height: 100vh;
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

.chapter-row {
  margin-bottom: 20px;
}

.preview-head-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chapter-select {
  width: 220px;
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
  color: #b85c38;
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

.smart-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
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
