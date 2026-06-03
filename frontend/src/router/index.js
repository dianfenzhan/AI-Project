import { createRouter, createWebHistory } from 'vue-router'
import Upload from '../views/Upload.vue'
import Generate from '../views/Generate.vue'
import Search from '../views/Search.vue'

const routes = [
  {
    path: '/',
    redirect: '/upload'
  },
  {
    path: '/upload',
    name: 'Upload',
    component: Upload
  },
  {
    path: '/generate',
    name: 'Generate',
    component: Generate
  },
  {
    path: '/search',
    name: 'Search',
    component: Search
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
