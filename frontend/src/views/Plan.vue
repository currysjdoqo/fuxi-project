<template>
  <Layout :username="username" :avatar="avatar" @show-profile="showProfileModal = true" @logout="handleLogout">
    <div class="plan-page">
      <header class="page-header">
        <div class="header-main">
          <h1>学习计划</h1>
          <p>按日期管理每日学习任务，保持和设置页一致的左右并排工作区布局。</p>
        </div>
      </header>

      <div class="plan-container">
        <section class="calendar-section">
          <el-card class="calendar-card">
            <el-date-picker
              v-model="selectedDate"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadPlanItems"
              class="date-picker"
            />
            <div class="date-info">
              <div class="date-display">
                <el-icon><Calendar /></el-icon>
                <span>{{ formatDate(selectedDate) }}</span>
              </div>
              <div class="stats">
                <span class="completed">{{ completedCount }} 项已完成</span>
                <span class="total">共 {{ totalCount }} 项任务</span>
              </div>
            </div>
          </el-card>
        </section>

        <section class="tasks-section">
          <el-card class="tasks-card">
            <div class="add-task">
              <el-input
                v-model="newTaskContent"
                placeholder="添加新的学习任务"
                @keyup.enter="addPlanItem"
                clearable
                class="task-input"
              >
                <template #append>
                  <el-button :icon="Plus" :loading="adding" @click="addPlanItem">添加</el-button>
                </template>
              </el-input>
            </div>

            <div class="tasks-list" v-loading="loading">
              <el-empty v-if="!loading && planItems.length === 0" description="当天还没有计划，先添加一项任务吧" />

              <div
                v-for="item in planItems"
                :key="item.id"
                class="task-item"
                :class="{ completed: item.completed === 1 }"
              >
                <el-checkbox
                  :model-value="item.completed === 1"
                  @change="toggleComplete(item)"
                  class="task-checkbox"
                />
                <span class="task-content">{{ item.content }}</span>
                <div class="task-actions">
                  <el-button v-if="editingId !== item.id" link :icon="Edit" @click="startEdit(item)" />
                  <el-button link type="danger" :icon="Delete" @click="deleteItem(item.id)" />
                </div>
              </div>

              <div v-if="editingId !== null" class="edit-form">
                <el-input v-model="editingContent" @keyup.enter="saveEdit" autofocus />
                <el-button type="primary" size="small" @click="saveEdit">保存</el-button>
                <el-button size="small" @click="cancelEdit">取消</el-button>
              </div>
            </div>
          </el-card>
        </section>
      </div>

      <ProfileModal v-model:visible="showProfileModal" :username="username" />
    </div>
  </Layout>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, Delete, Edit, Plus } from '@element-plus/icons-vue'
import {
  createPlanItem,
  deletePlanItem,
  getPlanItemsByDate,
  updatePlanItem
} from '../api'
import Layout from '../components/Layout/Layout.vue'
import ProfileModal from '../components/ProfileModal.vue'
import { useUser } from '../composables/useUser'
import { clearAuthSession } from '../utils/authStorage'

const router = useRouter()
const { username, avatar, loadUserInfo } = useUser()

const showProfileModal = ref(false)
const selectedDate = ref(getLocalDateString())
const planItems = ref([])
const newTaskContent = ref('')
const loading = ref(false)
const adding = ref(false)
const editingId = ref(null)
const editingContent = ref('')

const completedCount = computed(() => planItems.value.filter((item) => item.completed === 1).length)
const totalCount = computed(() => planItems.value.length)

function getLocalDateString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const handleLogout = () => {
  clearAuthSession()
  router.push('/auth/login')
  ElMessage.success('已退出登录')
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
}

const loadPlanItems = async () => {
  loading.value = true
  try {
    planItems.value = await getPlanItemsByDate(selectedDate.value)
  } catch {
    ElMessage.error('加载学习计划失败')
  } finally {
    loading.value = false
  }
}

const addPlanItem = async () => {
  if (!newTaskContent.value.trim()) {
    ElMessage.warning('请输入计划内容')
    return
  }
  adding.value = true
  try {
    await createPlanItem(selectedDate.value, newTaskContent.value.trim())
    newTaskContent.value = ''
    await loadPlanItems()
    ElMessage.success('学习计划已添加')
  } catch {
    ElMessage.error('添加学习计划失败')
  } finally {
    adding.value = false
  }
}

const toggleComplete = async (item) => {
  try {
    await updatePlanItem(item.id, {
      completed: item.completed === 1 ? 0 : 1
    })
    await loadPlanItems()
  } catch {
    ElMessage.error('更新任务状态失败')
  }
}

const startEdit = (item) => {
  editingId.value = item.id
  editingContent.value = item.content
}

const cancelEdit = () => {
  editingId.value = null
  editingContent.value = ''
}

const saveEdit = async () => {
  if (!editingContent.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  try {
    await updatePlanItem(editingId.value, { content: editingContent.value.trim() })
    cancelEdit()
    await loadPlanItems()
    ElMessage.success('任务已更新')
  } catch {
    ElMessage.error('更新任务失败')
  }
}

const deleteItem = async (itemId) => {
  try {
    await ElMessageBox.confirm('确定删除这条学习任务吗？', '删除任务', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消'
    })
  } catch {
    return
  }

  try {
    await deletePlanItem(itemId)
    await loadPlanItems()
    ElMessage.success('任务已删除')
  } catch {
    ElMessage.error('删除任务失败')
  }
}

onMounted(async () => {
  await loadUserInfo()
  await loadPlanItems()
})
</script>

<style scoped>
.plan-page {
  min-height: 100vh;
  padding: 22px 26px 32px 48px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 30px;
  color: #2f241b;
}

.page-header p {
  margin: 0;
  color: #736153;
  line-height: 1.65;
}

.plan-container {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: 18px;
}

.calendar-card,
.tasks-card {
  border-radius: 20px;
  border: 1px solid rgba(125, 86, 63, 0.12);
  box-shadow: 0 16px 32px rgba(96, 70, 50, 0.08);
  background: rgba(255, 252, 247, 0.92);
}

.date-picker {
  width: 100%;
  margin-bottom: 18px;
}

.date-info {
  padding: 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, #fbf2e8 0%, #f5e7d7 100%);
}

.date-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #2f241b;
  font-weight: 600;
  margin-bottom: 10px;
}

.stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.completed {
  color: #5c8a35;
  font-weight: 600;
}

.total {
  color: #6b5b45;
}

.tasks-card {
  min-height: 520px;
}

.add-task {
  margin-bottom: 18px;
}

.tasks-list {
  max-height: calc(100vh - 260px);
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f8f1e7;
  border-radius: 14px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.task-item:hover {
  background: #f2e3d1;
}

.task-item.completed {
  background: rgba(92, 138, 53, 0.1);
  opacity: 0.78;
}

.task-item.completed .task-content {
  text-decoration: line-through;
  color: #8b7b65;
}

.task-content {
  flex: 1;
  color: #2f241b;
}

.task-actions {
  display: flex;
  gap: 4px;
}

.edit-form {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: #fff8ef;
  border-radius: 14px;
}

.edit-form .el-input {
  flex: 1;
}

@media (max-width: 1180px) {
  .plan-page {
    padding: 18px 16px 28px;
  }

  .plan-container {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .page-header h1 {
    font-size: 24px;
  }
}
</style>
