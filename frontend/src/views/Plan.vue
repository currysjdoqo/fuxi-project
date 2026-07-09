<template>
  <div class="plan-page" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
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
      <header class="page-header">
        <el-button
          v-if="isMobileNav"
          circle
          text
          class="header-nav-btn"
          :icon="Menu"
          @click="toggleMobileNav"
        />
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
  Check,
  Menu
} from '@element-plus/icons-vue'
import { useSidebarLayout } from '../composables/useSidebarLayout'
import {
  createPlanItem,
  getPlanItemsByDate,
  updatePlanItem,
  deletePlanItem
} from '../api'

const router = useRouter()
const { sidebarCollapsed, mobileNavOpen, isMobileNav, toggleSidebar, toggleMobileNav, closeMobileNav } = useSidebarLayout()

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
  --sidebar-width: clamp(220px, 18vw, 256px);
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, rgba(184, 92, 56, 0.08) 0%, rgba(184, 92, 56, 0.04) 50%, rgba(139, 63, 31, 0.06) 100%);
}

.sidebar {
  width: var(--sidebar-width);
  flex: 0 0 var(--sidebar-width);
  background: linear-gradient(180deg, #3d2f24 0%, #2c2416 100%);
  color: #f8f4ec;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 2px 0 10px rgba(44, 36, 22, 0.15);
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-icon {
  font-size: 40px;
  color: #b85c38;
  margin-bottom: 12px;
}

.logo-section h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #f8f4ec;
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

.main-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 32px;
  color: #2c2416;
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 32px;
  font-weight: 700;
}

.page-header p {
  margin: 0;
  font-size: 16px;
  opacity: 0.8;
  color: #6b5b45;
}

.plan-container {
  display: flex;
  gap: 24px;
}

.calendar-section {
  flex: 0 0 auto;
  width: min(320px, 35vw);
  min-width: 260px;
}

.tasks-section {
  flex: 1;
  min-width: 0;
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
  background: linear-gradient(135deg, #f8f4ec 0%, #e8dfd0 100%);
  border-radius: 12px;
}

.date-display {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #2c2416;
  margin-bottom: 12px;
}

.stats {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.completed {
  color: #5c8a35;
  font-weight: 600;
}

.total {
  color: #6b5b45;
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
  background: #f8f4ec;
  border-radius: 12px;
  margin-bottom: 12px;
  transition: all 0.2s ease;
}

.task-item:hover {
  background: #e8dfd0;
  transform: translateX(4px);
}

.task-item.completed {
  background: rgba(92, 138, 53, 0.1);
  opacity: 0.7;
}

.task-item.completed .task-content {
  text-decoration: line-through;
  color: #8b7b65;
}

.task-checkbox {
  transform: scale(1.2);
}

.task-content {
  flex: 1;
  font-size: 15px;
  color: #2c2416;
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
