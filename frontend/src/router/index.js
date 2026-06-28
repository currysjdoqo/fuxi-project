import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Import from '../views/Import.vue'
import Review from '../views/Review.vue'
import Settings from '../views/Settings.vue'
import Trash from '../views/Trash.vue'
import Plan from '../views/Plan.vue'
import Register from '../views/Register.vue'
import Login from '../views/Login.vue'
import { getCurrentUser } from '../api'

const routes = [
  {
    path: '/auth',
    redirect: '/auth/login'
  },
  {
    path: '/auth/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/auth/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/import',
    name: 'Import',
    component: Import
  },
  {
    path: '/review',
    name: 'Review',
    component: Review
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  },
  {
    path: '/trash',
    name: 'Trash',
    component: Trash
  },
  {
    path: '/plan',
    name: 'Plan',
    component: Plan
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

let authCheckedToken = null
let authCheckedOk = false
const LOGIN_SESSION_KEY = 'auth_session_ok'

const clearLocalAuth = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('auth_username')
  sessionStorage.removeItem(LOGIN_SESSION_KEY)
}

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
    clearLocalAuth()
    return false
  }
}

router.beforeEach(async (to) => {
  const token = localStorage.getItem('auth_token')
  const sessionOk = sessionStorage.getItem(LOGIN_SESSION_KEY) === '1'

  if (to.path.startsWith('/auth')) {
    return true
  }

  if (!sessionOk) return '/auth/login'

  const isAuthenticated = await verifyToken(token)
  if (!isAuthenticated) return '/auth/login'
  return true
})

export default router
