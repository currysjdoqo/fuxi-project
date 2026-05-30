import { createRouter, createWebHistory } from 'vue-router'
import Import from '../views/Import.vue'
import WrongList from '../views/WrongList.vue'
import Review from '../views/Review.vue'
import Settings from '../views/Settings.vue'
import Trash from '../views/Trash.vue'
import Important from '../views/Important.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: () => import('../views/Home.vue')
  },
  {
    path: '/import',
    name: 'Import',
    component: Import
  },
  {
    path: '/wrong',
    name: 'WrongList',
    component: WrongList
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
    path: '/important',
    name: 'Important',
    component: Important
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
