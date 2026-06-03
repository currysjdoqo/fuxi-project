<template>
  <div class="plan-page">
    <div class="sidebar">
      <div class="logo-section">
        <el-icon class="logo-icon"><Document /></el-icon>
        <h2>学习计划</h2>
      </div>
      <nav class="nav-menu">
        <div class="nav-item active">
          <el-icon><List /></el-icon>
          <span>我的计划</span>
        </div>
        <div class="nav-item" @click="goToHome">
          <el-icon><Reading /></el-icon>
          <span>返回练习</span>
        </div>
      </nav>
    </div>

    <div class="main-content">
      <header class="page-header">
        <div class="header-left">
          <h1>我的学习计划</h1>
          <p>管理你的每日学习任务</p>
        </div>
      </header>

      <div class="plan-container">
        <div class="calendar-section">
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
                <span class="completed">{{ completedCount }} 已完成</span>
                <span class="total">{{ totalCount }} 总任务</span>
              </div>
            </div>
          </el-card>
        </div>

        <div class="tasks-section">
          <el-card class="tasks-card">
            <div class="add-task">
              <el-input
                v-model="newTaskContent"
                placeholder="添加新的学习计划..."
                @keyup.enter="addPlanItem"
                clearable
                class="task-input"
              >
                <template #append>
                  <el-button :icon="Plus" @click="addPlanItem" :loading="adding">添加</el-button>
                </template>
              </el-input>
            </div>

            <div class="tasks-list" v-loading="loading">
              <el-empty v-if="!loading && planItems.length === 0" description="今天还没有计划，开始添加吧！" />
              
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
                  <el-button
                    v-if="editingId !== item.id"
                    link
                    :icon="Edit"
                    @click="startEdit(item)"
                  />
                  <el-button
                    link
                    type="danger"
                    :icon="Delete"
                    @click="deleteItem(item.id)"
                  />
                </div>
              </div>

              <div v-if="editingId !== null" class="edit-form">
                <el-input
                  v-model="editingContent"
                  @keyup.enter="saveEdit"
                  autofocus
                />
                <el-button @click="saveEdit" type="primary" size="small">保存</el-button>
                <el-button @click="cancelEdit" size="small">取消</el-button>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Document,
  List,
  Reading,
  Calendar,
  Plus,
  Edit,
  Delete,
  Check
} from '@element-plus/icons-vue'
import {
  createPlanItem,
  getPlanItemsByDate,
  updatePlanItem,
  deletePlanItem
} from '../api'

const router = useRouter()

const getLocalDateString = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const selectedDate = ref(getLocalDateString())
const planItems = ref([])
const newTaskContent = ref('')
const loading = ref(false)
const adding = ref(false)
const editingId = ref(null)
const editingContent = ref('')

const completedCount = computed(() => planItems.value.filter(item => item.completed === 1).length)
const totalCount = computed(() => planItems.value.length)

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }
  return date.toLocaleDateString('zh-CN', options)
}

const loadPlanItems = async () => {
  loading.value = true
  try {
    const data = await getPlanItemsByDate(selectedDate.value)
    planItems.value = data
  } catch (error) {
    ElMessage.error('加载计划失败')
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
    await createPlanItem(selectedDate.value, newTaskContent.value)
    newTaskContent.value = ''
    await loadPlanItems()
    ElMessage.success('计划添加成功')
  } catch (error) {
    ElMessage.error('添加计划失败')
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
    if (item.completed === 0) {
      ElMessage.success('任务完成！🎉')
    }
  } catch (error) {
    ElMessage.error('更新状态失败')
  }
}

const startEdit = (item) => {
  editingId.value = item.id
  editingContent.value = item.content
}

const saveEdit = async () => {
  if (!editingContent.value.trim()) {
    ElMessage.warning('内容不能为空')
    return
  }
  try {
    await updatePlanItem(editingId.value, {
      content: editingContent.value
    })
    editingId.value = null
    editingContent.value = ''
    await loadPlanItems()
    ElMessage.success('更新成功')
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const cancelEdit = () => {
  editingId.value = null
  editingContent.value = ''
}

const deleteItem = async (itemId) => {
  try {
    await ElMessageBox.confirm('确定要删除这个计划吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deletePlanItem(itemId)
    await loadPlanItems()
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const goToHome = () => {
  router.push('/')
}

onMounted(() => {
  loadPlanItems()
})
</script>

<style scoped>
.plan-page {
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.sidebar {
  width: 240px;
  background: rgba(255, 255, 255, 0.95);
  color: #1e293b;
  display: flex;
  flex-direction: column;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.1);
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.logo-icon {
  font-size: 40px;
  color: #667eea;
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
  color: #64748b;
}

.nav-item:hover {
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
}

.nav-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.main-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 32px;
  color: white;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
}

.page-header p {
  margin: 0;
  font-size: 16px;
  opacity: 0.9;
}

.plan-container {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
}

.calendar-card {
  border: none;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.date-picker {
  width: 100%;
  margin-bottom: 20px;
}

.date-info {
  padding: 16px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  border-radius: 12px;
}

.date-display {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 12px;
}

.stats {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.completed {
  color: #22c55e;
  font-weight: 600;
}

.total {
  color: #64748b;
}

.tasks-card {
  border: none;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  min-height: 500px;
}

.add-task {
  margin-bottom: 24px;
}

.task-input {
  width: 100%;
}

.tasks-list {
  max-height: calc(100vh - 300px);
  overflow-y: auto;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.task-item:hover {
  background: #f1f5f9;
  transform: translateX(4px);
}

.task-item.completed {
  background: #f0fdf4;
  opacity: 0.7;
}

.task-item.completed .task-content {
  text-decoration: line-through;
  color: #94a3b8;
}

.task-checkbox {
  transform: scale(1.2);
}

.task-content {
  flex: 1;
  font-size: 15px;
  color: #1e293b;
}

.task-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.task-item:hover .task-actions {
  opacity: 1;
}

.edit-form {
  display: flex;
  gap: 8px;
  padding: 16px;
  background: #eff6ff;
  border-radius: 12px;
  margin-bottom: 12px;
}

.edit-form .el-input {
  flex: 1;
}
</style>
