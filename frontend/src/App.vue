<template>
  <div class="app-container">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </transition>
    </router-view>
  </div>
</template>

<script setup>
</script>

<style>
:root {
  --primary-color: #3b82f6;
  --success-color: #22c55e;
  --warning-color: #f59e0b;
  --danger-color: #ef4444;
  --info-color: #06b6d4;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Avenir Next', 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  color: #1e293b;
  background-color: #f5f7fa;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

#app {
  min-height: 100vh;
}

.app-container {
  min-height: 100vh;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

@media (max-width: 1200px) {
  .app-layout .practice-layout {
    grid-template-columns: minmax(260px, 32vw) minmax(0, 1fr) !important;
    gap: 16px !important;
    padding: 16px 18px 20px !important;
  }

  .app-layout .question-card {
    max-width: none !important;
    width: 100% !important;
  }

  .app-layout .subject-page,
  .app-layout .settings-content,
  .app-layout .review-content,
  .app-layout .wrong-content,
  .app-layout .important-content,
  .app-layout .trash-content,
  .app-layout .import-content {
    width: 100% !important;
    max-width: none !important;
  }

  .plan-page .plan-container {
    grid-template-columns: minmax(260px, 30vw) minmax(0, 1fr) !important;
  }
}

@media (max-width: 960px) {
  .app-layout,
  .plan-page {
    display: block !important;
  }

  .app-layout .sidebar,
  .plan-page .sidebar {
    position: static !important;
    width: 100% !important;
    height: auto !important;
    max-height: none !important;
  }

  .app-layout .main-content,
  .plan-page .main-content {
    margin-left: 0 !important;
    width: 100% !important;
    min-width: 0 !important;
  }

  .app-layout .page-header,
  .plan-page .page-header {
    flex-direction: column !important;
    align-items: flex-start !important;
    gap: 12px !important;
    padding: 16px !important;
  }

  .app-layout .type-filter,
  .app-layout .subject-page,
  .app-layout .practice-layout,
  .app-layout .settings-content,
  .app-layout .review-content,
  .app-layout .wrong-content,
  .app-layout .important-content,
  .app-layout .trash-content,
  .app-layout .import-content,
  .plan-page .plan-container {
    padding-left: 16px !important;
    padding-right: 16px !important;
  }

  .app-layout .practice-layout,
  .plan-page .plan-container {
    grid-template-columns: 1fr !important;
  }

  .app-layout .question-list {
    max-height: 280px !important;
  }

  .app-layout .question-card,
  .plan-page .calendar-card,
  .plan-page .tasks-card {
    padding: 18px !important;
  }

  .app-layout .stats-bar {
    flex-wrap: wrap !important;
    justify-content: flex-start !important;
    gap: 10px 20px !important;
    padding: 12px 16px !important;
  }
}

@media (max-width: 640px) {
  .app-layout .create-subject,
  .app-layout .header-actions,
  .app-layout .actions,
  .app-layout .attachment-header,
  .plan-page .date-info,
  .plan-page .stats {
    grid-template-columns: 1fr !important;
    flex-direction: column !important;
    align-items: stretch !important;
  }

  .app-layout .question-item,
  .app-layout .question-item.deleting {
    grid-template-columns: 30px minmax(0, 1fr) 18px 18px !important;
    gap: 8px !important;
    padding: 10px 12px !important;
  }

  .app-layout .question-item.deleting .el-checkbox {
    justify-self: center;
  }

  .app-layout .question-content {
    padding: 14px !important;
    font-size: 16px !important;
    line-height: 1.7 !important;
  }

  .app-layout .option-item,
  .app-layout .result-box,
  .app-layout .explanation-box {
    padding: 12px !important;
  }

  .app-layout .page-header h1,
  .plan-page .page-header h1 {
    font-size: 20px !important;
  }

  .app-layout .subject-grid,
  .app-layout .summary-grid,
  .app-layout .stats-grid,
  .app-layout .option-grid,
  .app-layout .upload-grid,
  .plan-page .stats {
    grid-template-columns: 1fr !important;
  }
}
</style>
