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
  --primary-color: #b85c38;
  --primary-dark: #8d3f1f;
  --primary-soft: rgba(184, 92, 56, 0.12);
  --success-color: #5c8a35;
  --warning-color: #b8860b;
  --danger-color: #a63434;
  --info-color: #3d7a8a;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Avenir Next', 'PingFang SC', 'Noto Sans SC', 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  color: #2c2416;
  background-color: #f4efe6;
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

.app-layout,
.plan-page {
  --app-sidebar-width: clamp(200px, 16vw, 228px);
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.app-sidebar-root {
  width: var(--app-sidebar-width);
  flex: 0 0 var(--app-sidebar-width);
  min-height: 100vh;
  position: relative;
  z-index: 100;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: #fff;
  background: linear-gradient(180deg, #3d2f24 0%, #2c2416 100%);
  transition: width 0.25s ease, flex-basis 0.25s ease, transform 0.25s ease, opacity 0.2s ease;
}

.sidebar-collapsed .app-sidebar-root {
  width: 0;
  flex-basis: 0;
  opacity: 0;
}

.app-sidebar-logo {
  padding: 24px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.app-sidebar-logo-icon {
  font-size: 40px;
  color: #b85c38;
}

.app-sidebar-logo-copy {
  min-width: 0;
}

.app-sidebar-logo-copy h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.app-sidebar-logo-copy span {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.app-sidebar-mobile-close {
  margin-left: auto;
  color: #cbd5e1;
}

.app-sidebar-nav {
  flex: 1;
  padding: 16px 12px;
  overflow-y: auto;
}

.app-sidebar-section-title {
  padding: 0 16px 10px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.app-sidebar-nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  color: #94a3b8;
  transition: all 0.2s ease;
}

.app-sidebar-nav-item:hover {
  background: rgba(184, 92, 56, 0.1);
  color: #e2e8f0;
}

.app-sidebar-nav-item.active {
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
  color: #fff;
}

.app-sidebar-nav-item .el-icon {
  font-size: 20px;
  min-width: 20px;
}

.app-sidebar-nav-item span {
  font-size: 14px;
  font-weight: 500;
}

.app-sidebar-user {
  padding: 16px 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.app-sidebar-user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.app-sidebar-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #e2e8f0;
  background: linear-gradient(135deg, #b85c38 0%, #8d3f1f 100%);
}

.app-sidebar-user-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.app-sidebar-username {
  font-weight: 500;
  font-size: 14px;
}

.app-sidebar-logout {
  font-size: 12px;
  color: #94a3b8;
  cursor: pointer;
}

.app-sidebar-logout:hover {
  color: #ef4444;
}

.desktop-sidebar-handle {
  position: fixed;
  top: 24px;
  left: calc(var(--app-sidebar-width) - 18px);
  z-index: 110;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(184, 92, 56, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #b85c38;
  font-size: 18px;
  line-height: 1;
  box-shadow: 0 10px 24px rgba(44, 36, 22, 0.12);
  cursor: pointer;
  transition: left 0.25s ease, background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.desktop-sidebar-handle:hover {
  background: #b85c38;
  color: #fff;
}

.desktop-sidebar-handle.collapsed {
  left: 12px;
}

.header-nav-btn {
  color: #334155;
  background: #f8fafc;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
}

.app-layout > .sidebar,
.plan-page > .sidebar {
  width: var(--app-sidebar-width, 240px) !important;
  flex: 0 0 var(--app-sidebar-width, 240px) !important;
  min-height: 100vh !important;
  position: relative !important;
  z-index: 100 !important;
  overflow: hidden !important;
  transition: width 0.25s ease, flex-basis 0.25s ease, transform 0.25s ease, opacity 0.2s ease !important;
}

.app-layout.sidebar-collapsed > .sidebar,
.plan-page.sidebar-collapsed > .sidebar {
  width: 0 !important;
  flex-basis: 0 !important;
  min-width: 0 !important;
  opacity: 0 !important;
}

.sidebar.open {
  transform: translateX(0);
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.logo-copy {
  min-width: 0;
}

.logo-copy h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.logo-copy span {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.logo-icon {
  font-size: 40px;
  color: #b85c38;
  flex-shrink: 0;
}

.mobile-close {
  display: none;
}

@media (max-width: 768px) {
  .mobile-close {
    display: flex;
  }
}

.nav-section-title {
  padding: 0 16px 10px;
  font-size: 11px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #64748b;
}

.logo-section {
  padding: 28px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
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

.user-section {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #f8f4ec;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.user-info:hover .avatar {
  transform: scale(1.05);
}

.user-details {
  min-width: 0;
}

.username {
  display: block;
  font-weight: 600;
  font-size: 15px;
  color: #f8f4ec;
}

.logout-btn {
  display: block;
  font-size: 12px;
  color: #a89985;
  margin-top: 2px;
  cursor: pointer;
  transition: color 0.2s ease;
}

.logout-btn:hover {
  color: #e8dfd0;
  background: rgba(166, 52, 52, 0.2);
  padding: 2px 6px;
  border-radius: 4px;
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

@media (max-width: 1180px) {
  .desktop-sidebar-handle {
    display: none !important;
  }

  .app-sidebar-root {
    position: fixed;
    top: 0;
    left: 0;
    width: min(82vw, 320px);
    max-width: 320px;
    flex-basis: auto;
    height: 100vh;
    transform: translateX(-100%);
    box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22);
  }

  .mobile-nav-open .app-sidebar-root {
    transform: translateX(0);
  }

  .sidebar-collapsed .app-sidebar-root {
    width: min(82vw, 320px);
    flex-basis: auto;
    opacity: 1;
  }

  .app-layout > .sidebar,
  .plan-page > .sidebar {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: min(82vw, 320px) !important;
    max-width: 320px !important;
    flex-basis: auto !important;
    height: 100vh !important;
    transform: translateX(-100%) !important;
    box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22) !important;
  }

  .app-layout.mobile-nav-open > .sidebar,
  .plan-page.mobile-nav-open > .sidebar {
    transform: translateX(0) !important;
  }

  .app-layout.sidebar-collapsed > .sidebar,
  .plan-page.sidebar-collapsed > .sidebar {
    width: min(82vw, 320px) !important;
    flex-basis: auto !important;
    opacity: 1 !important;
  }
}
</style>
