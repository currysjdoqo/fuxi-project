import { computed, onMounted, onUnmounted, ref } from 'vue'

const SIDEBAR_COLLAPSED_KEY = 'app_sidebar_collapsed'
const MOBILE_BREAKPOINT = 1180

export function useSidebarLayout() {
  const sidebarCollapsed = ref(false)
  const mobileNavOpen = ref(false)
  const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)
  const isMobileNav = computed(() => viewportWidth.value <= MOBILE_BREAKPOINT)

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
    if (isMobileNav.value) {
      mobileNavOpen.value = false
      sidebarCollapsed.value = false
      return
    }

    try {
      sidebarCollapsed.value = localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === 'true'
    } catch {
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

  return {
    sidebarCollapsed,
    mobileNavOpen,
    isMobileNav,
    toggleSidebar,
    toggleMobileNav,
    closeMobileNav
  }
}
