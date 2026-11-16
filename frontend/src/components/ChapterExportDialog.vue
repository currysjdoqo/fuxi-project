<template>
  <el-dialog
    v-model="dialogVisible"
    title="导出章节复习"
    width="520px"
    :close-on-click-modal="false"
    :close-on-press-escape="!exportLoading"
    :show-close="!exportLoading"
  >
    <div class="export-form">
      <div class="form-item">
        <label>导出章节{{ chapters.length > 1 ? '（按以下顺序合并）' : '' }}</label>
        <div class="chapter-list">
          <div v-for="(chapter, index) in chapters" :key="chapter.id" class="chapter-item">
            <span class="chapter-order">{{ index + 1 }}</span>
            <span class="chapter-name">{{ chapter.name }}</span>
          </div>
        </div>
      </div>

      <div class="form-item">
        <label>文件名</label>
        <el-input
          v-model="filename"
          :disabled="exportLoading"
          placeholder="请输入文件名"
          @blur="normalizeFilename"
        />
      </div>

      <div class="form-item">
        <label>导出格式</label>
        <el-radio-group
          v-model="exportFormat"
          :disabled="exportLoading"
          @change="handleFormatChange"
        >
          <el-radio value="pdf">PDF (.pdf)</el-radio>
          <el-radio value="docx">Word (.docx)</el-radio>
          <el-radio value="md">Markdown (.md)</el-radio>
        </el-radio-group>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button :disabled="exportLoading" @click="dialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="exportLoading"
          :disabled="!chapters.length"
          @click="handleExport"
        >
          <el-icon v-if="!exportLoading"><Download /></el-icon>
          {{ exportLoading ? '导出中...' : '导出' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Download } from '@element-plus/icons-vue'
import { exportChapterReview } from '../api/index.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  chapters: {
    type: Array,
    default: () => []
  },
  subjectName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const exportFormat = ref('pdf')
const filename = ref('')
const exportLoading = ref(false)

const getDefaultBaseName = () => {
  if (props.chapters.length === 1) {
    return props.chapters[0].name || '章节复习'
  }
  return `${props.subjectName || '科目'}-章节复习`
}

const stripKnownExtension = (name) => {
  return name.trim().replace(/(?:\.(?:pdf|docx|md))+$/i, '')
}

const getExportFilename = () => {
  const baseName = stripKnownExtension(filename.value) || getDefaultBaseName()
  return `${baseName}.${exportFormat.value}`
}

const normalizeFilename = () => {
  filename.value = getExportFilename()
}

const handleFormatChange = () => {
  normalizeFilename()
}

const parseDispositionFilename = (disposition) => {
  if (!disposition) return ''

  const encodedMatch = disposition.match(/filename\*\s*=\s*([^;]+)/i)
  if (encodedMatch) {
    let value = encodedMatch[1].trim().replace(/^"|"$/g, '')
    const charsetMatch = value.match(/^[^']*'[^']*'(.*)$/)
    if (charsetMatch) value = charsetMatch[1]
    try {
      return decodeURIComponent(value)
    } catch {
      return value
    }
  }

  const filenameMatch = disposition.match(/(?:^|;)\s*filename\s*=\s*(?:"([^"]*)"|([^;]*))/i)
  return (filenameMatch?.[1] || filenameMatch?.[2] || '').trim()
}

const getExportErrorMessage = async (error) => {
  const data = error?.response?.data
  if (data instanceof Blob) {
    try {
      const text = await data.text()
      try {
        const body = JSON.parse(text)
        if (typeof body.detail === 'string') return body.detail
        if (body.detail) return JSON.stringify(body.detail)
        return body.message || text || '未知错误'
      } catch {
        return text || error.message || '未知错误'
      }
    } catch {
      return error?.message || '未知错误'
    }
  }

  const detail = data?.detail
  if (typeof detail === 'string') return detail
  if (detail) return JSON.stringify(detail)
  return error?.message || '未知错误'
}

const handleExport = async () => {
  if (exportLoading.value || !props.chapters.length) return

  exportLoading.value = true
  try {
    const exportFilename = getExportFilename()
    filename.value = exportFilename
    const response = await exportChapterReview(
      props.chapters.map(chapter => chapter.id),
      exportFormat.value,
      exportFilename
    )

    const disposition = response.headers?.['content-disposition']
    const downloadFilename = parseDispositionFilename(disposition) || exportFilename
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = downloadFilename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
    dialogVisible.value = false
  } catch (error) {
    ElMessage.error(`导出失败：${await getExportErrorMessage(error)}`)
  } finally {
    exportLoading.value = false
  }
}

watch(dialogVisible, (visible) => {
  if (visible) {
    exportFormat.value = 'pdf'
    filename.value = `${getDefaultBaseName()}.pdf`
  }
})
</script>

<style scoped>
.export-form {
  padding: 4px 0;
}

.form-item {
  margin-bottom: 20px;
}

.form-item label {
  display: block;
  margin-bottom: 10px;
  font-weight: 500;
  color: #333;
}

.chapter-list {
  max-height: 220px;
  overflow-y: auto;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 6px 12px;
  background: #faf9f7;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.chapter-item + .chapter-item {
  border-top: 1px solid #eee;
}

.chapter-order {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f2e5dc;
  color: #b85c38;
  font-size: 12px;
  line-height: 22px;
  text-align: center;
}

.chapter-name {
  color: #333;
  font-size: 14px;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
