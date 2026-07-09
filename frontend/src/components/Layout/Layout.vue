<template>
  <div class="app-layout" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile-nav-open': mobileNavOpen }">
    <div v-if="mobileNavOpen" class="mobile-nav-mask" @click="closeMobileNav"></div>
    <Sidebar
      :sidebar-collapsed="sidebarCollapsed"
      :mobile-nav-open="mobileNavOpen"
      :username="username"
      :avatar="avatar"
      @close-mobile="closeMobileNav"
      @show-profile="$emit('show-profile')"
      @logout="$emit('logout')"
    >
      <template #nav-items>
        <slot name="nav-items" />
      </template>
    </Sidebar>

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
      <slot />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Sidebar from './Sidebar.vue'

defineProps({
  username: {
    type: String,
    default: ''
  },
  avatar: {
    type: String,
    default: ''
  }
})

defineEmits(['show-profile', 'logout'])

const SIDEBAR_COLLAPSED_KEY = 'sidebar_collapsed'

const sidebarCollapsed = ref(false)
const mobileNavOpen = ref(false)
const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

const isMobileNav = computed(() => viewportWidth.value < 768)

const saveSidebarState = () => {
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, String(sidebarCollapsed.value))
}

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  saveSidebarState()
}

const toggleMobileNav = () => {
  mobileNavOpen.value = !mobileNavOpen.value
}

const closeMobileNav = () => {
  mobileNavOpen.value = false
}

const syncLayoutMode = () => {
  viewportWidth.value = window.innerWidth
  if (viewportWidth.value >= 768) {
    mobileNavOpen.value = false
    sidebarCollapsed.value = false
    return
  }
  const stored = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
  if (stored !== null) {
    sidebarCollapsed.value = stored === 'true'
  } else {
    sidebarCollapsed.value = false
  }
}

onMounted(() => {
  syncLayoutMode()
  window.addEventListener('resize', syncLayoutMode)
})

onUnmounted(() => {
  window.removeEventListener('resize', syncLayoutMode)
})

defineExpose({
  toggleMobileNav
})
</script>

<style scoped>
.app-layout {
  --sidebar-width: clamp(220px, 18vw, 256px);
  --primary-color: #b85c38;
  --primary-dark: #8d3f1f;
  --primary-light: rgba(184, 92, 56, 0.12);
  --success-color: #5c8a35;
  --warning-color: #b8860b;
  --danger-color: #a63434;
  --text-primary: #2c2416;
  --text-secondary: #6b5b45;
  --text-muted: #8b7b65;
  --bg-primary: #ffffff;
  --bg-secondary: #f8f4ec;
  --bg-gradient-start: #f4efe6;
  --bg-gradient-end: #f1e7d8;
  --border-color: #e8dfd0;
  --shadow-sm: 0 1px 2px 0 rgba(44, 36, 22, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(44, 36, 22, 0.1), 0 2px 4px -1px rgba(44, 36, 22, 0.06);
  --shadow-lg: 0 10px 15px -3px rgba(44, 36, 22, 0.1), 0 4px 6px -2px rgba(44, 36, 22, 0.05);
  --shadow-xl: 0 20px 25px -5px rgba(44, 36, 22, 0.1), 0 10px 10px -5px rgba(44, 36, 22, 0.04);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  display: flex;
  min-height: 100vh;
  background: linear-gradient(135deg, rgba(184, 92, 56, 0.08) 0%, rgba(184, 92, 56, 0.04) 50%, rgba(139, 63, 31, 0.06) 100%);
  background-attachment: fixed;
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.main-content {
  flex: 1;
  position: relative;
  min-width: 0;
  min-height: 100vh;
}

.desktop-sidebar-handle {
  position: absolute;
  top: 20px;
  left: -18px;
  width: 36px;
  height: 36px;
  border: 1px solid rgba(184, 92, 56, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  color: #b85c38;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(44, 36, 22, 0.1);
}

.desktop-sidebar-handle:hover {
  background: #b85c38;
  color: white;
  border-color: #b85c38;
}

.desktop-sidebar-handle.collapsed {
  left: 10px;
}

@media (max-width: 768px) {
  .desktop-sidebar-handle {
    display: none;
  }
}
</style>