<template>
  <el-dialog
    v-model="dialogVisible"
    title="导出习题"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="export-form">
      <!-- 科目信息 -->
      <div class="info-section">
        <el-alert
          :title="`科目：${subjectName}`"
          type="info"
          :closable="false"
          show-icon
        />
        <el-alert
          :title="`共 ${totalQuestions} 道题目`"
          type="info"
          :closable="false"
          show-icon
          style="margin-top: 10px;"
        />
      </div>

      <!-- 导出格式 -->
      <div class="form-item">
        <label>导出格式</label>
        <el-radio-group v-model="exportFormat" size="default">
          <el-radio value="word">Word 文档 (.docx)</el-radio>
          <el-radio value="pdf">PDF 文档 (.pdf)</el-radio>
        </el-radio-group>
      </div>

      <!-- 导出内容 -->
      <div class="form-item">
        <label>导出内容</label>
        <el-checkbox v-model="includeAnswer">包含答案</el-checkbox>
        <el-checkbox v-model="includeAnalysis">包含解析（如有）</el-checkbox>
      </div>

      <!-- 题目类型过滤 -->
      <div class="form-item">
        <label>题目类型（默认全部）</label>
        <div class="type-tags">
          <el-tag
            v-for="type in availableTypes"
            :key="type.value"
            :type="selectedTypes.includes(type.value) ? 'primary' : 'info'"
            class="type-tag"
            @click="toggleType(type.value)"
            style="cursor: pointer;"
          >
            {{ type.label }}
          </el-tag>
        </div>
        <div class="type-hint" v-if="selectedTypes.length === 0">
          默认导出所有支持的题目类型
        </div>
      </div>

      <!-- 预览区域 -->
      <div class="preview-section" v-if="previewQuestions.length > 0">
        <div class="preview-header">
          <span class="preview-title">预览（前5题）</span>
        </div>
        <div class="preview-list">
          <div
            v-for="(q, index) in previewQuestions"
            :key="q.id || index"
            class="preview-item"
          >
            <div class="preview-type">{{ getTypeLabel(q.type) }}</div>
            <div class="preview-content">{{ truncateContent(q.content) }}</div>
            <div class="preview-answer" v-if="includeAnswer && q.answer">
              答案：{{ q.answer }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handlePreview" :loading="previewLoading">
          预览
        </el-button>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleExport" :loading="exportLoading">
          <el-icon v-if="!exportLoading"><Download /></el-icon>
          {{ exportLoading ? '导出中...' : '导出' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue'
import { exportQuestions, previewExport, getExportTypes } from '../api/index.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  subjectId: {
    type: [Number, String],
    required: true
  },
  subjectName: {
    type: String,
    default: ''
  },
  totalQuestions: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

// 导出选项
const exportFormat = ref('word')
const includeAnswer = ref(true)
const includeAnalysis = ref(true)
const selectedTypes = ref([])

// 预览数据
const previewQuestions = ref([])
const previewLoading = ref(false)
const exportLoading = ref(false)

// 可用题目类型
const availableTypes = ref([
  { value: 'single', label: '单选题' },
  { value: 'multiple', label: '多选题' },
  { value: 'judge', label: '判断题' },
  { value: 'fill', label: '填空题' },
  { value: 'short_answer', label: '简答题' }
])

// 切换题目类型
const toggleType = (type) => {
  const index = selectedTypes.value.indexOf(type)
  if (index > -1) {
    selectedTypes.value.splice(index, 1)
  } else {
    selectedTypes.value.push(type)
  }
}

// 获取类型标签
const getTypeLabel = (type) => {
  const typeMap = {
    'single': '【单选题】',
    'multiple': '【多选题】',
    'judge': '【判断题】',
    'fill': '【填空题】',
    'short_answer': '【简答题】',
    'programming': '【编程题】'
  }
  return typeMap[type] || '【未知】'
}

// 截断内容
const truncateContent = (content) => {
  if (!content) return ''
  return content.length > 80 ? content.substring(0, 80) + '...' : content
}

// 预览
const handlePreview = async () => {
  previewLoading.value = true
  try {
    const data = await previewExport(
      props.subjectId,
      exportFormat.value,
      includeAnswer.value,
      includeAnalysis.value
    )
    previewQuestions.value = data.preview_questions || []
    ElMessage.success('预览已更新')
  } catch (error) {
    console.error('预览失败:', error)
    ElMessage.error('预览失败：' + (error.message || '未知错误'))
  } finally {
    previewLoading.value = false
  }
}

// 导出
const handleExport = async () => {
  exportLoading.value = true
  try {
    const blob = await exportQuestions(props.subjectId, {
      format: exportFormat.value,
      includeAnswer: includeAnswer.value,
      includeAnalysis: includeAnalysis.value,
      questionTypes: selectedTypes.value.length > 0 ? selectedTypes.value : null
    })

    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // 获取文件名
    const contentDisposition = link.getAttribute('data-content-disposition')
    let filename = `${props.subjectName}_练习题.${exportFormat.value === 'pdf' ? 'pdf' : 'docx'}`

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (filenameMatch) {
        filename = decodeURIComponent(filenameMatch[1].replace(/['"]/g, ''))
      }
    }

    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功！')
    dialogVisible.value = false
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败：' + (error.message || '未知错误'))
  } finally {
    exportLoading.value = false
  }
}

// 监听对话框打开
watch(dialogVisible, (val) => {
  if (val) {
    // 重置选项
    previewQuestions.value = []
    selectedTypes.value = []
  }
})
</script>

<style scoped>
.export-form {
  padding: 10px 0;
}

.info-section {
  margin-bottom: 20px;
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

.type-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.type-tag {
  user-select: none;
}

.type-hint {
  margin-top: 8px;
  font-size: 12px;
  color: #999;
}

.preview-section {
  margin-top: 20px;
  border-top: 1px solid #eee;
  padding-top: 15px;
}

.preview-header {
  margin-bottom: 10px;
}

.preview-title {
  font-weight: 500;
  color: #666;
}

.preview-list {
  max-height: 300px;
  overflow-y: auto;
}

.preview-item {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 8px;
}

.preview-type {
  font-size: 12px;
  color: #409eff;
  margin-bottom: 5px;
}

.preview-content {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
}

.preview-answer {
  margin-top: 5px;
  font-size: 12px;
  color: #67c23a;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
