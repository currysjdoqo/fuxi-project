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
  display: flex;
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(184, 92, 56, 0.16), transparent 28%),
    linear-gradient(135deg, #f7f1e7 0%, #f3ece1 52%, #ebe0d3 100%);
}

.mobile-nav-mask {
  position: fixed;
  inset: 0;
  background: rgba(24, 18, 12, 0.45);
  z-index: 90;
}

.main-content {
  flex: 1;
  min-width: 0;
  min-height: 100vh;
  position: relative;
}

.desktop-sidebar-handle {
  position: absolute;
  top: 20px;
  left: 12px;
  z-index: 20;
  width: 28px;
  height: 56px;
  border: none;
  border-radius: 14px;
  background: rgba(61, 47, 36, 0.9);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;
}

.desktop-sidebar-handle:hover {
  background: rgba(47, 36, 27, 0.96);
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
