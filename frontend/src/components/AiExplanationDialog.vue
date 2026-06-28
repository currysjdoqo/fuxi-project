<template>
  <el-dialog
    v-model="dialogVisible"
    title="AI 题目讲解"
    width="700px"
    :close-on-click-modal="true"
  >
    <div class="explanation-content" v-loading="loading">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <el-icon class="is-loading"><Loading /></el-icon>
        <p>正在生成讲解，请稍候...</p>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state">
        <el-alert
          :title="error"
          type="error"
          :closable="false"
          show-icon
        />
      </div>

      <!-- 讲解内容 -->
      <div v-else-if="explanation" class="explanation-text">
        <div class="markdown-body" v-html="renderedExplanation"></div>
      </div>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <p>暂无讲解内容</p>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleRefresh" :loading="loading" :disabled="!questionId">
          重新生成
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { getAiExplanation } from '../api/index.js'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  questionId: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['update:visible'])

const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const loading = ref(false)
const error = ref('')
const explanation = ref('')

// 简单的 Markdown 渲染（基础实现）
const renderedExplanation = computed(() => {
  if (!explanation.value) return ''

  let html = explanation.value

  // 标题处理
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')

  // 列表处理
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')

  // 换行处理
  html = html.replace(/\n\n/g, '</p><p>')
  html = '<p>' + html + '</p>'

  // 清理多余的 p 标签
  html = html.replace(/<p><\/p>/g, '')
  html = html.replace(/<p>(<h[23]>)/g, '$1')
  html = html.replace(/(<\/h[23]>)<\/p>/g, '$1')
  html = html.replace(/<p>(<ul>)/g, '$1')
  html = html.replace(/(<\/ul>)<\/p>/g, '$1')

  // 加粗处理
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  return html
})

// 加载讲解
const loadExplanation = async () => {
  if (!props.questionId) return

  loading.value = true
  error.value = ''
  explanation.value = ''

  try {
    const result = await getAiExplanation(props.questionId)

    if (result.success) {
      explanation.value = result.explanation
    } else {
      if (result.error === 'API_KEY_NOT_CONFIGURED') {
        error.value = result.message
      } else {
        error.value = result.message || '获取讲解失败'
      }
    }
  } catch (err) {
    console.error('获取讲解失败:', err)
    error.value = err.response?.data?.detail || '获取讲解失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

// 重新生成
const handleRefresh = () => {
  loadExplanation()
}

// 监听对话框打开
watch(dialogVisible, (val) => {
  if (val && props.questionId) {
    loadExplanation()
  }
})

// 监听题目变化
watch(() => props.questionId, (newVal) => {
  if (dialogVisible.value && newVal) {
    loadExplanation()
  }
})
</script>

<style scoped>
.explanation-content {
  min-height: 200px;
  max-height: 500px;
  overflow-y: auto;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: #909399;
}

.loading-state .el-icon {
  font-size: 32px;
  margin-bottom: 16px;
}

.loading-state p {
  margin: 0;
  font-size: 14px;
}

.error-state {
  padding: 20px;
}

.error-state .el-alert {
  width: 100%;
}

.explanation-text {
  padding: 10px 0;
}

.markdown-body {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.markdown-body :deep(h2) {
  font-size: 16px;
  color: #409eff;
  margin: 16px 0 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.markdown-body :deep(h3) {
  font-size: 15px;
  color: #67c23a;
  margin: 12px 0 6px;
}

.markdown-body :deep(p) {
  margin: 8px 0;
}

.markdown-body :deep(ul) {
  margin: 8px 0;
  padding-left: 20px;
}

.markdown-body :deep(li) {
  margin: 4px 0;
}

.markdown-body :deep(strong) {
  color: #f56c6c;
  font-weight: 600;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
