import { createRouter, createWebHistory } from 'vue-router'
import { getCurrentUser } from '../api'
import { bootstrapLegacyAuth, clearAuthSession, getAuthToken, isAuthSessionReady } from '../utils/authStorage'

const routes = [
  {
    path: '/auth',
    redirect: '/auth/login'
  },
  {
    path: '/auth/register',
    name: 'Register',
    component: () => import('../views/Register.vue')
  },
  {
    path: '/auth/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/import',
    name: 'Import',
    component: () => import('../views/Import.vue')
  },
  {
    path: '/review',
    name: 'Review',
    component: () => import('../views/Review.vue')
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue')
  },
  {
    path: '/trash',
    name: 'Trash',
    component: () => import('../views/Trash.vue')
  },
  {
    path: '/plan',
    name: 'Plan',
    component: () => import('../views/Plan.vue')
  },
  {
    path: '/friends',
    name: 'Friends',
    component: () => import('../views/Friends.vue')
  },
  {
    path: '/chapters',
    name: 'Chapters',
    component: () => import('../views/Chapters.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let authCheckedToken = null
let authCheckedOk = false

const verifyToken = async (token) => {
  if (!token) return false
  if (token === authCheckedToken) return authCheckedOk

  try {
    await getCurrentUser()
    authCheckedToken = token
    authCheckedOk = true
    return true
  } catch {
    authCheckedToken = null
    authCheckedOk = false
    clearAuthSession()
    return false
  }
}

router.beforeEach(async (to) => {
  bootstrapLegacyAuth()
  const token = getAuthToken()
  const sessionOk = isAuthSessionReady()

  if (to.path.startsWith('/auth')) {
    return true
  }

  if (!sessionOk) return '/auth/login'

  const isAuthenticated = await verifyToken(token)
  if (!isAuthenticated) return '/auth/login'
  return true
})

export default router
