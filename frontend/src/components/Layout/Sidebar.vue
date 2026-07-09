<template>
  <nav class="sidebar" :class="{ collapsed: sidebarCollapsed, open: mobileNavOpen }">
    <div class="logo-section">
      <div class="logo-group">
        <el-icon class="logo-icon"><Document /></el-icon>
        <div class="logo-copy">
          <h2>习题管理系统</h2>
          <span>Practice Workspace</span>
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
          :class="{ active: $route.path === item.path }"
          @click="goToPath(item.path)"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </div>
      </slot>
    </div>

    <div class="user-section">
      <div class="user-info">
        <div class="avatar" :style="{ background: avatar ? `url(${avatar}) center/cover` : undefined }" @click="$emit('show-profile')">
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
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Document, List, Plus, Refresh, Delete, Setting, Close } from '@element-plus/icons-vue'

const props = defineProps({
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
  return window.innerWidth < 768
})

const defaultNavItems = [
  { path: '/', label: '练习模式', icon: Document },
  { path: '/plan', label: '学习计划', icon: List },
  { path: '/import', label: '导入习题', icon: Plus },
  { path: '/review', label: '复习模式', icon: Refresh },
  { path: '/trash', label: '垃圾桶', icon: Delete },
  { path: '/settings', label: '设置', icon: Setting }
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
  flex: 0 0 var(--sidebar-width, clamp(220px, 18vw, 256px));
  background: linear-gradient(180deg, #3d2f24 0%, #2c2416 100%);
  color: #f8f4ec;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 100vh;
  z-index: 100;
  overflow: hidden;
  transition: width 0.25s ease, flex-basis 0.25s ease, transform 0.25s ease, opacity 0.2s ease;
  box-shadow: 0 10px 15px -3px rgba(44, 36, 22, 0.1), 0 4px 6px -2px rgba(44, 36, 22, 0.05);
}

.sidebar.collapsed {
  width: 0;
  flex-basis: 0;
  opacity: 0;
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
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    transform: translateX(-100%);
    z-index: 200;
  }
  .sidebar.open {
    transform: translateX(0);
  }
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
</style>