import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/upload',
    redirect: { path: '/', query: { tab: 'tenant-upload' } }
  },
  {
    path: '/search',
    redirect: { path: '/', query: { tab: 'search' } }
  },
  {
    path: '/generate',
    redirect: { path: '/', query: { tab: 'generate' } }
  }
]

const router = createRouter({
  history: createWebHistory('/seo-frontend/'),
  routes
})

export default router
