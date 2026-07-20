<template>
  <Layout ref="layoutRef" :username="username" :avatar="avatar" @show-profile="showProfileModal = true" @logout="handleLogout">
    <div class="trash-page">
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
            <h1>垃圾桶</h1>
            <p>删除的题目会先保留在这里，可以恢复；永久删除后不可找回。</p>
          </div>
          <div class="header-actions">
            <el-select v-model="subjectId" clearable placeholder="全部科目" class="subject-select" @change="loadTrash">
              <el-option v-for="subject in subjects" :key="subject.id" :label="subject.name" :value="subject.id" />
            </el-select>
            <el-button :icon="Refresh" @click="loadTrash">刷新</el-button>
          </div>
        </header>

        <section class="toolbar">
          <span>已选 {{ selectedIds.length }} / {{ trashList.length }}</span>
          <el-button size="small" @click="selectAll">全选</el-button>
          <el-button size="small" @click="selectedIds = []">清空</el-button>
          <el-button size="small" type="success" :disabled="!selectedIds.length" :loading="restoring" @click="restoreSelected">
            恢复选中
          </el-button>
          <el-button size="small" type="danger" :disabled="!selectedIds.length" :loading="deleting" @click="permanentDeleteSelected">
            彻底删除选中
          </el-button>
        </section>

        <section class="table-panel">
          <el-table :data="trashList" border v-loading="loading" empty-text="垃圾桶为空">
            <el-table-column width="52" align="center">
              <template #default="{ row }">
                <el-checkbox :model-value="selectedIds.includes(row.id)" @change="toggleSelection(row.id)" />
              </template>
            </el-table-column>
            <el-table-column prop="subject_name" label="科目" width="130" />
            <el-table-column label="题型" width="90" align="center">
              <template #default="{ row }">{{ questionTypeLabel(row.type) }}</template>
            </el-table-column>
            <el-table-column label="题干" min-width="280">
              <template #default="{ row }">
                <div class="stem">{{ row.content }}</div>
              </template>
            </el-table-column>
            <el-table-column label="答案" width="150">
              <template #default="{ row }">{{ displayAnswer(row) }}</template>
            </el-table-column>
            <el-table-column label="删除时间" width="180">
              <template #default="{ row }">{{ formatDate(row.deleted_at) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="190" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="success" @click="restoreOne(row.id)">恢复</el-button>
                <el-button size="small" type="danger" @click="permanentDelete(row.id)">永久删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <ProfileModal
          v-model:visible="showProfileModal"
          :username="username"
        />
    </div>
  </Layout>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleClose, Delete, Menu, Refresh, Star } from '@element-plus/icons-vue'
import { useUser } from '../composables/useUser'
import { clearAuthSession } from '../utils/authStorage'
import {
  getSubjects,
  getTrashQuestions,
  permanentlyDeleteQuestion,
  permanentlyDeleteTrashQuestions,
  restoreTrashQuestions
} from '../api'
import ProfileModal from '../components/ProfileModal.vue'
import Layout from '../components/Layout/Layout.vue'

const router = useRouter()
const { username, avatar, loadUserInfo } = useUser()
const showProfileModal = ref(false)
const layoutRef = ref(null)
const isMobileNav = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)

const toggleMobileNav = () => {
  layoutRef.value?.toggleMobileNav()
}
const subjects = ref([])
const subjectId = ref(null)
const trashList = ref([])
const selectedIds = ref([])
const loading = ref(false)
const restoring = ref(false)
const deleting = ref(false)

const handleLogout = () => {
  clearAuthSession()
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

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

const formatDate = (value) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const loadSubjects = async () => {
  subjects.value = await getSubjects()
}

const loadTrash = async () => {
  loading.value = true
  try {
    trashList.value = await getTrashQuestions(subjectId.value)
    selectedIds.value = selectedIds.value.filter((id) => trashList.value.some((item) => item.id === id))
  } catch (error) {
    ElMessage.error(`加载垃圾桶失败：${error.response?.data?.detail || error.message}`)
  } finally {
    loading.value = false
  }
}

const toggleSelection = (questionId) => {
  if (selectedIds.value.includes(questionId)) {
    selectedIds.value = selectedIds.value.filter((id) => id !== questionId)
    return
  }
  selectedIds.value = [...selectedIds.value, questionId]
}

const selectAll = () => {
  selectedIds.value = trashList.value.map((item) => item.id)
}

const restoreSelected = async () => {
  if (!selectedIds.value.length) return
  restoring.value = true
  try {
    await restoreTrashQuestions(selectedIds.value)
    ElMessage.success('题目已恢复')
    selectedIds.value = []
    await loadTrash()
  } catch (error) {
    ElMessage.error(`恢复失败：${error.response?.data?.detail || error.message}`)
  } finally {
    restoring.value = false
  }
}

const restoreOne = async (questionId) => {
  selectedIds.value = [questionId]
  await restoreSelected()
}

const permanentDeleteSelected = async () => {
  if (!selectedIds.value.length) return

  try {
    await ElMessageBox.confirm(
      `确认彻底删除选中的 ${selectedIds.value.length} 道题？该操作不可恢复。`,
      '彻底删除',
      {
        type: 'warning',
        confirmButtonText: '彻底删除',
        cancelButtonText: '取消'
      }
    )
  } catch {
    return
  }

  deleting.value = true
  try {
    await permanentlyDeleteTrashQuestions(selectedIds.value)
    ElMessage.success('选中题目已彻底删除')
    selectedIds.value = []
    await loadTrash()
  } catch (error) {
    ElMessage.error(`批量彻底删除失败：${error.response?.data?.detail || error.message}`)
  } finally {
    deleting.value = false
  }
}

const permanentDelete = async (questionId) => {
  try {
    await ElMessageBox.confirm('确认永久删除这道题？该操作不可恢复。', '永久删除', {
      type: 'warning',
      confirmButtonText: '永久删除',
      cancelButtonText: '取消'
    })
    await permanentlyDeleteQuestion(questionId)
    ElMessage.success('题目已永久删除')
    selectedIds.value = selectedIds.value.filter((id) => id !== questionId)
    await loadTrash()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`永久删除失败：${error.response?.data?.detail || error.message}`)
    }
  }
}

onMounted(async () => {
  await loadUserInfo()
  await loadSubjects()
  await loadTrash()
})
</script>

<style scoped>
.trash-page {
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

.header-actions,
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subject-select {
  width: 180px;
}

.toolbar {
  padding: 14px 20px 0;
}

.toolbar span {
  color: #606266;
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
