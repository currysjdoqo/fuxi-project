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
        <!-- 未分章题目卡片 -->
        <div v-if="unassignedCount > 0" class="chapter-card unassigned-card" @click="showUnassigned = true">
          <div class="card-header">
            <span class="card-name">未分章题目</span>
            <el-tag size="small" type="warning">{{ unassignedCount }} 题</el-tag>
          </div>
          <div class="card-footer">
            <span class="not-extracted">点击查看题目并 AI 划分章节</span>
          </div>
        </div>
        <div v-if="!chapters.length && unassignedCount === 0 && !loadingChapters" class="empty-state">
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
              v-for="q in (knowledge.questions || [])"
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
            <div v-if="!(knowledge.questions && knowledge.questions.length)" class="empty-block">
              <p>该章节暂无题目</p>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>

    <!-- 未分章题目弹窗 -->
    <el-dialog v-model="showUnassigned" title="未分章题目" width="720px" @open="loadUnassignedDetail">
      <div v-loading="loadingUnassigned" class="unassigned-dialog">
        <div class="dialog-actions">
          <el-button
            type="warning"
            plain
            :loading="assigning"
            @click="handleAiAssignUnassigned"
          >
            <el-icon style="margin-right: 4px"><MagicStick /></el-icon>
            AI 自动划分全部
          </el-button>
          <el-divider direction="vertical" />
          <el-select
            v-model="manualChapterId"
            placeholder="选择目标章节"
            style="width: 200px"
            :disabled="!unassignedQuestions.length"
          >
            <el-option
              v-for="ch in chapters"
              :key="ch.id"
              :label="ch.name"
              :value="ch.id"
            />
            <el-option label="+ 新建章节…" :value="0" />
          </el-select>
          <el-input
            v-if="manualChapterId === 0"
            v-model="newChapterName"
            placeholder="输入章节名"
            style="width: 160px"
          />
          <el-button
            type="primary"
            plain
            :disabled="!manualChapterId || selectedUnassignedIds.length === 0"
            :loading="moving"
            @click="handleManualMove"
          >
            移动选中 {{ selectedUnassignedIds.length }} 题
          </el-button>
        </div>
        <div v-if="unassignedQuestions.length" class="unassigned-list">
          <div class="select-all-row">
            <el-checkbox
              v-model="selectAllUnassigned"
              :indeterminate="isIndeterminate"
              @change="handleSelectAll"
            >全选</el-checkbox>
            <span class="count-text">共 {{ unassignedQuestions.length }} 道未分章题目</span>
          </div>
          <div v-for="q in unassignedQuestions" :key="q.id" class="question-item">
            <el-checkbox
              :model-value="selectedUnassignedIds.includes(q.id)"
              @change="(val) => toggleSelect(q.id, val)"
              style="margin-right: 8px"
            />
            <el-tag size="small" type="info" style="margin-right: 8px">{{ typeLabel(q.type) }}</el-tag>
            <span class="q-content">{{ q.content }}</span>
          </div>
        </div>
        <div v-else-if="!loadingUnassigned" class="empty-block">
          <p>没有未分章的题目</p>
        </div>
      </div>
    </el-dialog>
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
  extractAllKnowledge,
  getUnassignedQuestions,
  aiAssignUnassigned,
  moveQuestionsToChapter,
  createChapter
} from '../api'

const subjects = ref([])
const chapters = ref([])
const selectedSubjectId = ref(null)
const selectedChapter = ref(null)
const loadingChapters = ref(false)

// 章节详情数据
const knowledge = ref({ questions: [], summary_md: null, outline: null })
const activeTab = ref('summary')

// AI 操作 loading
const extracting = ref(false)
const generatingSummary = ref(false)
const generatingOutline = ref(false)
const tagging = ref(false)

// 未分章题目
const unassignedCount = ref(0)
const showUnassigned = ref(false)
const unassignedQuestions = ref([])
const loadingUnassigned = ref(false)
const assigning = ref(false)

// 手动划分
const manualChapterId = ref(null)
const newChapterName = ref('')
const selectedUnassignedIds = ref([])
const moving = ref(false)

const selectAllUnassigned = computed({
  get: () => unassignedQuestions.value.length > 0 && selectedUnassignedIds.value.length === unassignedQuestions.value.length,
  set: (val) => { selectedUnassignedIds.value = val ? unassignedQuestions.value.map(q => q.id) : [] }
})

const isIndeterminate = computed(() => {
  return selectedUnassignedIds.value.length > 0 && selectedUnassignedIds.value.length < unassignedQuestions.value.length
})

const handleSelectAll = (val) => {
  selectedUnassignedIds.value = val ? unassignedQuestions.value.map(q => q.id) : []
}

const toggleSelect = (id, val) => {
  if (val) {
    if (!selectedUnassignedIds.value.includes(id)) {
      selectedUnassignedIds.value.push(id)
    }
  } else {
    selectedUnassignedIds.value = selectedUnassignedIds.value.filter(qid => qid !== id)
  }
}

const handleManualMove = async () => {
  if (!selectedUnassignedIds.value.length) {
    ElMessage.warning('请先勾选题目')
    return
  }
  let targetChapterId = manualChapterId.value
  moving.value = true
  try {
    // 如果选了新建章节
    if (targetChapterId === 0) {
      const name = newChapterName.value.trim()
      if (!name) {
        ElMessage.warning('请输入章节名')
        moving.value = false
        return
      }
      const ch = await createChapter(selectedSubjectId.value, name)
      targetChapterId = ch.id
      newChapterName.value = ''
    }
    await moveQuestionsToChapter(targetChapterId, selectedUnassignedIds.value)
    ElMessage.success(`已将 ${selectedUnassignedIds.value.length} 道题目移动到章节`)
    selectedUnassignedIds.value = []
    manualChapterId.value = null
    await loadUnassignedDetail()
    await loadChapters()
  } catch (error) {
    ElMessage.error(`移动失败：${error.response?.data?.detail || error.message}`)
  } finally {
    moving.value = false
  }
}

const typeLabel = (t) => {
  const map = { single: '单选', judge: '判断', fill: '填空', short: '简答' }
  return map[t] || t
}

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
    // 刷新未分章题目数
    try {
      const unassigned = await getUnassignedQuestions(selectedSubjectId.value)
      unassignedCount.value = unassigned.count
    } catch {
      unassignedCount.value = 0
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
  knowledge.value = { questions: [], summary_md: null, outline: null }
  await loadKnowledge(ch.id)
}

const backToList = () => {
  selectedChapter.value = null
  loadChapters() // 刷新提炼状态
}

const loadUnassignedDetail = async () => {
  if (!selectedSubjectId.value) return
  loadingUnassigned.value = true
  try {
    const data = await getUnassignedQuestions(selectedSubjectId.value)
    unassignedQuestions.value = data.questions
    unassignedCount.value = data.count
  } catch (error) {
    ElMessage.error('加载未分章题目失败')
  } finally {
    loadingUnassigned.value = false
  }
}

const handleAiAssignUnassigned = async () => {
  assigning.value = true
  try {
    const result = await aiAssignUnassigned(selectedSubjectId.value)
    if (result.errors?.length) {
      ElMessage.warning(`部分失败：${result.errors.join('；')}`)
    }
    ElMessage.success(result.message)
    showUnassigned.value = false
    await loadChapters() // 刷新章节列表（含新建的章节）
  } catch (error) {
    ElMessage.error(`AI 划分失败：${error.response?.data?.detail || error.message}`)
  } finally {
    assigning.value = false
  }
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

.unassigned-card {
  border-color: #e6a23c;
  border-style: dashed;
  background: #fdf6ec;
}

.unassigned-card:hover {
  border-color: #e6a23c;
  background: #faecd8;
}

.dialog-actions {
  margin-bottom: 16px;
}

.unassigned-list {
  max-height: 400px;
  overflow-y: auto;
}

.unassigned-list .question-item {
  background: #faf9f7;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 8px;
  display: flex;
  align-items: flex-start;
  gap: 4px;
}

.unassigned-list .q-content {
  font-size: 14px;
  flex: 1;
}

.select-all-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #eee;
  margin-bottom: 8px;
}

.count-text {
  font-size: 13px;
  color: #999;
}

.dialog-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
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
