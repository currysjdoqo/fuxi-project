<template>
  <div class="chapters-page">
    <!-- 章节列表视图 -->
    <div v-if="!selectedChapter" class="chapter-list-view">
      <div class="page-header">
        <h2>章节复习</h2>
        <p class="hint">选择章节查看 AI 提炼的知识点总结、知识大纲和题目标签</p>
      </div>

      <div class="selector-row">
        <el-select
          v-model="selectedSubjectId"
          placeholder="选择科目"
          style="width: 240px"
          @change="loadChapters"
        >
          <el-option
            v-for="s in subjects"
            :key="s.id"
            :label="s.name"
            :value="s.id"
          />
        </el-select>
      </div>

      <div v-if="selectedSubjectId" v-loading="loadingChapters" class="chapter-cards">
        <div
          v-for="ch in chapters"
          :key="ch.id"
          class="chapter-card"
          @click="openChapter(ch)"
        >
          <div class="card-header">
            <span class="card-name">{{ ch.name }}</span>
            <el-tag size="small" type="info">{{ ch.question_count }} 题</el-tag>
          </div>
          <div class="card-footer">
            <el-icon v-if="ch.has_summary || ch.has_outline || ch.has_tags" class="extracted-icon"><CircleCheck /></el-icon>
            <span v-if="ch.has_summary || ch.has_outline || ch.has_tags" class="extracted-text">已提炼</span>
            <span v-else class="not-extracted">未提炼</span>
            <span v-if="ch.wrong_count" class="wrong-count">错题 {{ ch.wrong_count }}</span>
          </div>
        </div>
        <div v-if="!chapters.length && !loadingChapters" class="empty-state">
          该科目暂无章节，请先在导入页面分章导入题目
        </div>
      </div>
    </div>

    <!-- 章节详情视图 -->
    <div v-else class="chapter-detail-view">
      <div class="detail-header">
        <el-button :icon="ArrowLeft" text @click="backToList">返回章节列表</el-button>
        <h3>{{ selectedChapter.name }}</h3>
        <el-button
          type="primary"
          :loading="extracting"
          @click="handleExtractAll"
        >
          <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
          一键提炼本章
        </el-button>
      </div>

      <el-tabs v-model="activeTab" class="detail-tabs">
        <!-- 知识点总结 -->
        <el-tab-pane label="知识点总结" name="summary">
          <div v-if="extracting" v-loading="true" class="loading-block" />
          <div v-else-if="knowledge.summary_md" class="summary-content">
            <div class="summary-meta">
              <el-tag size="small" type="success">已生成</el-tag>
              <span v-if="knowledge.summary_generated_at" class="meta-time">
                {{ formatTime(knowledge.summary_generated_at) }}
              </span>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="generatingSummary"
                @click="handleGenerateSummary"
              >重新生成</el-button>
            </div>
            <div class="markdown-body" v-html="renderedSummary"></div>
          </div>
          <div v-else class="empty-block">
            <p>尚未生成知识点总结</p>
            <el-button
              type="primary"
              :loading="generatingSummary"
              @click="handleGenerateSummary"
            >生成知识点总结</el-button>
          </div>
        </el-tab-pane>

        <!-- 知识大纲 -->
        <el-tab-pane label="知识大纲" name="outline">
          <div v-if="extracting" v-loading="true" class="loading-block" />
          <div v-else-if="knowledge.outline && knowledge.outline.length" class="outline-content">
            <div class="summary-meta">
              <el-tag size="small" type="success">已生成</el-tag>
              <span v-if="knowledge.outline_generated_at" class="meta-time">
                {{ formatTime(knowledge.outline_generated_at) }}
              </span>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="generatingOutline"
                @click="handleGenerateOutline"
              >重新生成</el-button>
            </div>
            <el-tree
              :data="knowledge.outline"
              :props="{ label: 'title', children: 'children' }"
              default-expand-all
              :expand-on-click-node="true"
              class="outline-tree"
            />
          </div>
          <div v-else class="empty-block">
            <p>尚未生成知识大纲</p>
            <el-button
              type="primary"
              :loading="generatingOutline"
              @click="handleGenerateOutline"
            >生成知识大纲</el-button>
          </div>
        </el-tab-pane>

        <!-- 本章题目 -->
        <el-tab-pane label="本章题目" name="questions">
          <div class="questions-content">
            <div class="summary-meta" v-if="knowledge.tags_generated_at">
              <el-tag size="small" type="success">标签已生成</el-tag>
              <span class="meta-time">{{ formatTime(knowledge.tags_generated_at) }}</span>
              <el-button
                size="small"
                type="primary"
                plain
                :loading="tagging"
                @click="handleTagQuestions"
              >重新打标签</el-button>
            </div>
            <div v-else class="summary-meta">
              <el-button
                size="small"
                type="primary"
                plain
                :loading="tagging"
                @click="handleTagQuestions"
              >AI 打知识点标签</el-button>
            </div>
            <div
              v-for="q in knowledge.questions"
              :key="q.id"
              class="question-item"
            >
              <div class="q-content">{{ q.content }}</div>
              <div class="q-answer">答案：{{ q.answer }}</div>
              <div v-if="q.knowledge_tags && q.knowledge_tags.length" class="q-tags">
                <el-tag
                  v-for="tag in q.knowledge_tags"
                  :key="tag"
                  size="small"
                  effect="plain"
                >{{ tag }}</el-tag>
              </div>
            </div>
            <div v-if="!knowledge.questions.length" class="empty-block">
              <p>该章节暂无题目</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowLeft, CircleCheck, MagicStick } from '@element-plus/icons-vue'
import {
  getSubjects,
  getChapters,
  getChapterKnowledge,
  tagChapterQuestions,
  generateChapterSummary,
  generateChapterOutline,
  extractAllKnowledge
} from '../api'

const subjects = ref([])
const chapters = ref([])
const selectedSubjectId = ref(null)
const selectedChapter = ref(null)
const loadingChapters = ref(false)

// 章节详情数据
const knowledge = ref({})
const activeTab = ref('summary')

// AI 操作 loading
const extracting = ref(false)
const generatingSummary = ref(false)
const generatingOutline = ref(false)
const tagging = ref(false)

// 简单 Markdown 渲染（不引入外部库，处理基本语法）
const renderedSummary = computed(() => {
  const md = knowledge.value.summary_md || ''
  if (!md) return ''
  let html = md
    // 标题
    .replace(/^### (.+)$/gm, '<h4>$1</h4>')
    .replace(/^## (.+)$/gm, '<h3>$1</h3>')
    .replace(/^# (.+)$/gm, '<h2>$1</h2>')
    // 粗体
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // 列表项
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // 段落
    .replace(/\n\n/g, '</p><p>')
    .replace(/^(?!<[hl])(.+)$/gm, '<p>$1</p>')
  // 包裹连续 li
  html = html.replace(/(<li>.*?<\/li>(?:\s*<li>.*?<\/li>)*)/gs, '<ul>$1</ul>')
  html = html.replace(/<p><ul>/g, '<ul>').replace(/<\/ul><\/p>/g, '</ul>')
  html = html.replace(/<p><h/g, '<h').replace(/<\/h(\d)><\/p>/g, '</h$1>')
  return html
})

const formatTime = (dt) => {
  if (!dt) return ''
  const d = new Date(dt)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

onMounted(async () => {
  try {
    const data = await getSubjects()
    subjects.value = data
    if (data.length) {
      selectedSubjectId.value = data[0].id
      await loadChapters()
    }
  } catch (error) {
    ElMessage.error('加载科目失败')
  }
})

const loadChapters = async () => {
  if (!selectedSubjectId.value) {
    chapters.value = []
    return
  }
  loadingChapters.value = true
  try {
    const data = await getChapters(selectedSubjectId.value)
    // 检查提炼状态
    for (const ch of data) {
      ch.has_summary = false
      ch.has_outline = false
      ch.has_tags = false
    }
    chapters.value = data
    // 并行获取每章的提炼状态
    for (const ch of chapters.value) {
      try {
        const k = await getChapterKnowledge(ch.id)
        ch.has_summary = !!k.summary_md
        ch.has_outline = !!(k.outline && k.outline.length)
        ch.has_tags = !!k.tags_generated_at
      } catch {
        // 忽略单章错误
      }
    }
  } catch (error) {
    ElMessage.error('加载章节失败')
  } finally {
    loadingChapters.value = false
  }
}

const openChapter = async (ch) => {
  selectedChapter.value = ch
  activeTab.value = 'summary'
  await loadKnowledge(ch.id)
}

const backToList = () => {
  selectedChapter.value = null
  loadChapters() // 刷新提炼状态
}

const loadKnowledge = async (chapterId) => {
  try {
    knowledge.value = await getChapterKnowledge(chapterId)
  } catch (error) {
    ElMessage.error('加载知识点数据失败')
  }
}

const handleTagQuestions = async () => {
  tagging.value = true
  try {
    const result = await tagChapterQuestions(selectedChapter.value.id)
    ElMessage.success(result.message)
    if (result.errors?.length) {
      ElMessage.warning(`部分失败：${result.errors.join('；')}`)
    }
    await loadKnowledge(selectedChapter.value.id)
  } catch (error) {
    ElMessage.error(`打标签失败：${error.response?.data?.detail || error.message}`)
  } finally {
    tagging.value = false
  }
}

const handleGenerateSummary = async () => {
  generatingSummary.value = true
  try {
    const result = await generateChapterSummary(selectedChapter.value.id)
    if (result.errors?.length) {
      ElMessage.warning(`部分失败：${result.errors.join('；')}`)
    }
    if (result.summary_md) {
      ElMessage.success('知识点总结已生成')
    } else {
      ElMessage.error('生成失败')
    }
    await loadKnowledge(selectedChapter.value.id)
  } catch (error) {
    ElMessage.error(`生成总结失败：${error.response?.data?.detail || error.message}`)
  } finally {
    generatingSummary.value = false
  }
}

const handleGenerateOutline = async () => {
  generatingOutline.value = true
  try {
    const result = await generateChapterOutline(selectedChapter.value.id)
    if (result.errors?.length) {
      ElMessage.warning(`部分失败：${result.errors.join('；')}`)
    }
    if (result.outline?.length) {
      ElMessage.success('知识大纲已生成')
    } else {
      ElMessage.error('生成失败')
    }
    await loadKnowledge(selectedChapter.value.id)
  } catch (error) {
    ElMessage.error(`生成大纲失败：${error.response?.data?.detail || error.message}`)
  } finally {
    generatingOutline.value = false
  }
}

const handleExtractAll = async () => {
  extracting.value = true
  try {
    const result = await extractAllKnowledge(selectedChapter.value.id)
    if (result.errors?.length) {
      ElMessage.warning(`部分失败：${result.errors.join('；')}`)
    }
    ElMessage.success(result.message)
    await loadKnowledge(selectedChapter.value.id)
    // 刷新列表中的提炼状态
    const ch = chapters.value.find(c => c.id === selectedChapter.value.id)
    if (ch) {
      ch.has_summary = result.has_summary
      ch.has_outline = result.has_outline
      ch.has_tags = result.tagged_count > 0
    }
  } catch (error) {
    ElMessage.error(`提炼失败：${error.response?.data?.detail || error.message}`)
  } finally {
    extracting.value = false
  }
}
</script>

<style scoped>
.chapters-page {
  padding: 24px;
  max-width: 1000px;
  margin: 0 auto;
}

.page-header h2 {
  margin: 0 0 4px;
  font-size: 22px;
}

.page-header .hint {
  margin: 0 0 20px;
  color: #999;
  font-size: 14px;
}

.selector-row {
  margin-bottom: 20px;
}

.chapter-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.chapter-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 12px;
  padding: 18px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
}

.chapter-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-color: #d99873;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-name {
  font-size: 16px;
  font-weight: 600;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #999;
}

.extracted-icon {
  color: #67c23a;
}

.extracted-text {
  color: #67c23a;
  font-weight: 500;
}

.not-extracted {
  color: #c0c4cc;
}

.wrong-count {
  margin-left: auto;
  color: #f56c6c;
}

.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 48px;
  color: #c0c4cc;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.detail-header h3 {
  margin: 0;
  flex: 1;
  font-size: 18px;
}

.detail-tabs {
  min-height: 400px;
}

.loading-block,
.empty-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: #999;
  gap: 16px;
}

.summary-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  font-size: 13px;
}

.meta-time {
  color: #999;
}

.markdown-body {
  line-height: 1.8;
  font-size: 14px;
}

.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  margin: 16px 0 8px;
  font-weight: 600;
}

.markdown-body :deep(ul) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-body :deep(li) {
  margin-bottom: 4px;
}

.markdown-body :deep(strong) {
  color: #b85c38;
}

.outline-tree {
  margin-top: 12px;
}

.outline-tree :deep(.el-tree-node__content) {
  height: 36px;
  font-size: 14px;
}

.questions-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.question-item {
  background: #faf9f7;
  border-radius: 8px;
  padding: 14px 16px;
}

.q-content {
  font-size: 14px;
  margin-bottom: 6px;
}

.q-answer {
  font-size: 13px;
  color: #67c23a;
  margin-bottom: 8px;
}

.q-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
