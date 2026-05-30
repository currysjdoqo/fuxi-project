<template>
  <div class="settings-page">
    <header class="page-header">
      <div>
        <h1>设置</h1>
        <p>配置 AI 讲解和数据管理。</p>
      </div>
    </header>

    <main class="settings-content">
      <section class="settings-card">
        <h2>DeepSeek API Key</h2>
        <p class="muted">
          后端会保存到项目根目录的 .env 文件。当前状态：{{ settings?.has_deepseek_api_key ? '已配置' : '未配置' }}
        </p>
        <div class="key-row">
          <el-input
            v-model="apiKey"
            type="password"
            show-password
            placeholder="sk-..."
            autocomplete="off"
          />
          <el-button type="primary" :icon="Check" :loading="saving" @click="saveKey">保存</el-button>
        </div>
      </section>

      <section class="settings-card">
        <h2>错题移除阈值</h2>
        <p class="muted">答对错题达到该次数后，才会从错题本移除（1-10）。</p>
        <div class="threshold-row">
          <el-input-number v-model="wrongThreshold" :min="1" :max="10" />
          <el-button type="primary" :icon="Check" :loading="savingThreshold" @click="saveThreshold">保存</el-button>
        </div>
      </section>

      <section class="settings-card danger">
        <h2>清空所有数据</h2>
        <p class="muted">会删除题目、练习记录和错题本，操作不可撤销。</p>
        <el-button type="danger" :icon="Delete" :loading="clearing" @click="clearData">清空所有数据</el-button>
      </section>
    </main>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Delete } from '@element-plus/icons-vue'
import { clearAllData, getSettings, saveDeepSeekKey, saveWrongThreshold } from '../api'

const settings = ref(null)
const apiKey = ref('')
const saving = ref(false)
const clearing = ref(false)
const wrongThreshold = ref(1)
const savingThreshold = ref(false)

const loadSettings = async () => {
  try {
    settings.value = await getSettings()
    wrongThreshold.value = settings.value?.wrong_question_remove_threshold || 1
  } catch (error) {
    ElMessage.error(`加载设置失败：${error.response?.data?.detail || error.message}`)
  }
}

const saveThreshold = async () => {
  savingThreshold.value = true
  try {
    await saveWrongThreshold(wrongThreshold.value)
    ElMessage.success('错题移除阈值已保存')
    await loadSettings()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    savingThreshold.value = false
  }
}

const saveKey = async () => {
  if (!apiKey.value.trim()) {
    ElMessage.warning('请输入 API Key')
    return
  }
  saving.value = true
  try {
    await saveDeepSeekKey(apiKey.value.trim())
    apiKey.value = ''
    ElMessage.success('API Key 已保存')
    await loadSettings()
  } catch (error) {
    ElMessage.error(`保存失败：${error.response?.data?.detail || error.message}`)
  } finally {
    saving.value = false
  }
}

const clearData = async () => {
  try {
    await ElMessageBox.confirm('确认删除所有题目、练习记录和错题本？', '清空所有数据', {
      type: 'warning',
      confirmButtonText: '确认清空',
      cancelButtonText: '取消'
    })
    clearing.value = true
    await clearAllData()
    localStorage.removeItem('exercise-review-session')
    ElMessage.success('所有数据已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(`清空失败：${error.response?.data?.detail || error.message}`)
    }
  } finally {
    clearing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 49px);
}

.page-header {
  padding: 18px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
}

.page-header h1 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #303133;
}

.page-header p,
.muted {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.settings-content {
  max-width: 780px;
  margin: 20px auto;
  padding: 0 20px;
  display: grid;
  gap: 16px;
}

.settings-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 20px;
}

.settings-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #303133;
}

.settings-card.danger {
  border-color: #f3d0d0;
}

.key-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  margin-top: 16px;
}

.threshold-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}

@media (max-width: 680px) {
  .key-row {
    grid-template-columns: 1fr;
  }
}
</style>
