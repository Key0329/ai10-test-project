import { createRouter, createWebHashHistory } from 'vue-router'

import Dashboard from './pages/Dashboard.vue'
import NewJob from './pages/NewJob.vue'
import JobDetail from './pages/JobDetail.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/new', component: NewJob },
  { path: '/jobs/:id', component: JobDetail, props: true },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
