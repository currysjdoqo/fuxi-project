<template>
  <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, open: mobileNavOpen }">
    <div class="logo-section">
      <div class="logo-group">
        <el-icon class="logo-icon"><Document /></el-icon>
        <div class="logo-copy">
          <h2>习题管理系统</h2>
          <span>学习与账户中心</span>
        </div>
      </div>
      <el-button
        v-if="isMobileNav"
        circle
        text
        class="sidebar-toggle mobile-close"
        :icon="Close"
        @click="$emit('close-mobile')"
      />
    </div>

    <div class="nav-menu">
      <div class="nav-section-title">功能导航</div>
      <slot name="nav-items">
        <div
          v-for="item in defaultNavItems"
          :key="item.path"
          class="nav-item"
          :class="{ active: route.path === item.path }"
          @click="goToPath(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </slot>
    </div>

    <div class="user-section">
      <div class="user-info">
        <div
          class="avatar"
          :style="{ background: avatar ? `url(${avatar}) center/cover` : undefined }"
          @click="$emit('show-profile')"
        >
          <template v-if="!avatar">{{ username.charAt(0).toUpperCase() }}</template>
        </div>
        <div class="user-details">
          <span class="username">{{ username }}</span>
          <span class="logout-btn" @click="$emit('logout')">退出登录</span>
        </div>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Close, Delete, Document, List, Plus, Refresh, Setting, UserFilled } from '@element-plus/icons-vue'

defineProps({
  sidebarCollapsed: {
    type: Boolean,
    default: false
  },
  mobileNavOpen: {
    type: Boolean,
    default: false
  },
  username: {
    type: String,
    default: ''
  },
  avatar: {
    type: String,
    default: ''
  }
})

defineEmits(['close-mobile', 'show-profile', 'logout'])

const router = useRouter()
const route = useRoute()

const isMobileNav = computed(() => {
  if (typeof window === 'undefined') return false
  return window.innerWidth <= 1180
})

const defaultNavItems = [
  { path: '/', label: '练习模式', icon: Document },
  { path: '/plan', label: '学习计划', icon: List },
  { path: '/import', label: '导入习题', icon: Plus },
  { path: '/review', label: '复习模式', icon: Refresh },
  { path: '/trash', label: '垃圾桶', icon: Delete },
  { path: '/friends', label: '好友互动', icon: UserFilled },
  { path: '/settings', label: '设置中心', icon: Setting }
]

const goToPath = (path) => {
  if (route.path !== path) {
    router.push(path)
  }
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-width, clamp(220px, 18vw, 256px));
  background: linear-gradient(180deg, #3d2f24 0%, #2b2219 100%);
  color: #f8f4ec;
  display: flex;
  flex-direction: column;
  position: relative;
  flex: 0 0 var(--sidebar-width, clamp(220px, 18vw, 256px));
  min-height: 100vh;
  z-index: 100;
  transition: width 0.24s ease, transform 0.24s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: 84px;
  flex-basis: 84px;
}

.sidebar.collapsed .logo-copy,
.sidebar.collapsed .nav-section-title,
.sidebar.collapsed .nav-item span,
.sidebar.collapsed .user-details {
  opacity: 0;
  pointer-events: none;
}

.logo-section {
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo-group {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.logo-icon {
  font-size: 30px;
  color: #d99873;
  flex-shrink: 0;
}

.logo-copy h2 {
  margin: 0;
  font-size: 18px;
  color: #fffaf1;
}

.logo-copy span {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.64);
}

.nav-menu {
  flex: 1;
  padding: 18px 12px;
  overflow-y: auto;
}

.nav-section-title {
  margin: 0 8px 10px;
  font-size: 12px;
  letter-spacing: 0.08em;
  color: rgba(255, 255, 255, 0.45);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  cursor: pointer;
  color: #ccbfae;
  transition: all 0.2s ease;
  margin-bottom: 6px;
}

.nav-item:hover {
  background: rgba(217, 152, 115, 0.12);
  color: #fff9f1;
}

.nav-item.active {
  background: linear-gradient(135deg, #b85c38 0%, #8e4528 100%);
  color: #fff;
  box-shadow: 0 10px 24px rgba(142, 69, 40, 0.24);
}

.nav-item .el-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.user-section {
  padding: 16px 18px 22px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  cursor: pointer;
  flex-shrink: 0;
}

.user-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.username {
  font-size: 14px;
  color: #fffaf1;
}

.logout-btn {
  font-size: 12px;
  color: #c9b8a4;
  cursor: pointer;
}

.logout-btn:hover {
  color: #fffaf1;
}

@media (max-width: 1180px) {
  .sidebar {
    position: fixed;
    inset: 0 auto 0 0;
    transform: translateX(-100%);
    z-index: 200;
    width: min(280px, 78vw);
  }

  .sidebar.open {
    transform: translateX(0);
  }
}
</style>
